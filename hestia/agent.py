from qdrant_client import QdrantClient, models
from qdrant_client.models import VectorParams, PointStruct, ScoredPoint

import itertools
from copy import deepcopy
from typing import Optional, Dict, Any, Literal, List, Tuple, Protocol, Sequence, Set, Callable, get_args
from dataclasses import dataclass, field, asdict
import uuid
import requests
from pathlib import Path

import hestia.logger as logger
import hestia.settings as settings

log = logger.logger(__name__)
log.setLevel(settings.LOG_LEVEL)

logHandler = logger.logging.FileHandler(settings.LOG_FILE, mode='a')
formatter = logger.logging.Formatter("%(asctime)s - %(levelname)s - %(funcName)s() : %(message)s", "%Y-%m-%d %H:%M:%S")
logHandler.setFormatter(formatter)
log.addHandler(logHandler)


DB_URL = settings.DB_URL
LLM_URL = settings.LLM_URL

REQUEST_TIMEOUT = settings.REQUEST_TIMEOUT

DEFAULT_GEN_MODEL = settings.DEFAULT_GEN_MODEL
DEFAULT_EMBEDDING_MODEL = settings.DEFAULT_EMB_MODEL
DEFAULT_RERANKER_MODEL = settings.DEFAULT_RRK_MODEL

DEFAULT_CONFIG = {
    "vectors":{
        "Default": {
            "size": 1024,
            "distance": "Cosine"
        }
    }
}

from concurrent.futures import ThreadPoolExecutor, as_completed

Mode = Literal["simple", "q2e", "hyDE", ] # "cot", "contrast""hybrid", "extract", , 
_AVAILABLE_MODES = list(get_args(Mode))
Ranking = Literal["rrf", "dbsf", "max_score"]
_ALLOWED_RANKINGS = set(get_args(Ranking))

@dataclass(frozen=True)
class StepFlow:
    requires: Set[str]
    produces: Set[str]

@dataclass(frozen=True)
class StepDefinition:
    flow: StepFlow
    method: str | None

STEP_DEFS = {
    "PASS_THROUGH": StepDefinition(
        flow=StepFlow(requires=set(), produces={"queries"}),
        method=None,
    ),
    "LLM_GENERATE": StepDefinition(
        flow=StepFlow(requires=set(), produces={"queries"}),
        method="generate",
    ),
    "EMBED": StepDefinition(
        flow=StepFlow(requires={"queries"}, produces={"embeddings"}),
        method="embed",
    ),
    "RERANK": StepDefinition(
        flow=StepFlow(requires={"points"}, produces={"points"}),
        method="rerank",
    ),
    "VECTOR_SEARCH": StepDefinition(
        flow=StepFlow(requires={"embeddings"}, produces={"points"}),
        method="retrieve",
    ),  
}

def _deep_merge(self, base: dict, override: dict) -> dict:
        out = deepcopy(base)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out

@dataclass
class OptionsBase:
    @classmethod
    def from_dict(cls, d: dict):
        return cls(**d)

    @classmethod
    def from_schema(cls, schema: dict):
        return cls(**schema)

@dataclass
class LLMConfig(OptionsBase):
    model: str
    temperature: Optional[float] = 0.0
    num_predict: int = 1
    raw: bool = False

@dataclass
class EmbConfig(OptionsBase):
    model: str
    vector_size: Optional[int] = 1024

@dataclass
class QueryOptions(OptionsBase):
    """
    TODO:
    - source defaults from settings.py
    """
    using: str = "Default"
    ranking: Ranking = "rrf"
    limit: int = 5
    offset: int = 0
    with_payload: bool = True
    with_vectors: bool = False
    prefetch_limit: Optional[int] = 0
    score_threshold: Optional[float] = None
    filter: Optional[object] = None


@dataclass
class ExecutionContext:
    llm: LLMConfig
    rrk: LLMConfig
    emb: EmbConfig
    query: QueryOptions

@dataclass
class Request(OptionsBase):
    type: str | None = None

@dataclass
class QueryRequest(Request):
    query: str | None = None
    collection: str | None = None

@dataclass
class RAGRequest(QueryRequest):
    mode: Mode | None = None


@dataclass
class UpsertOptions(OptionsBase):
    collection: str
    vectors: Dict[str, Any]

@dataclass(frozen=True)
class QueryStep:
    type: str
    options: dict | None = None
    payload: Any | None = None
    flow: StepFlow | None = None


@dataclass(frozen=True)
class QueryPlan:
    query: str
    mode : Mode
    steps: List[QueryStep] = None

    def validate(self) -> bool:
        available: set[str] = set()
        for idx, step in enumerate(self.steps):
            if step.flow is None:
                log.warning(f"Step {idx} ('{step.type}') has no flow defined.")
                return False
            
            missing = step.flow.requires - available
            if missing:
                log.warning(f"Step {idx} ('{step.type}') requires {missing} "
                            f"but only {available} are available.")
                return False
            # Advance the flow
            available |= step.flow.produces
        return True

    def ascii(self) -> str:
        lines = []

        for step in self.steps:
            if step.flow and step.flow.requires:
                inp = ", ".join(step.flow.requires)
            else:
                inp = "∅"

            out = ", ".join(step.flow.produces) if step.flow else "∅"
            lines.append(f"{inp} ──▶ {step.type} ──▶ {out}")

        return "\n".join(lines)
    
    def __repr__(self):
        return self.ascii()


@dataclass
class QueryContext:
    org_query: str                            # original query
    queries: List[str] = None       # potentially generated queries used for retrieval

    embeddings: List[List[float]] = field(default_factory=dict) # query-embeddings pairs
    points: Dict[str, Any] = field(default_factory=dict)     # retrieved points

    def __repr__(self) -> str:
        return (
            f"QueryContext("
            f"orgiginal query: {self.org_query!r}, "
            f"generated queries: {len(self.queries)}, "
            f"embeddings: {self._repr_embeddings()}, "
            f"points: {self.points or None}"
            f")"
        )

    @staticmethod
    def _summarize_embedding(v):
        # Works for lists, numpy arrays, torch tensors
        try:
            return f"vector(shape={len(v)})"
        except Exception:
            return "<embedding>"

    def _repr_embeddings(self):
        if not self.embeddings:
            return "{}"
        summary = [self._summarize_embedding(v) for v in self.embeddings]
        return summary


@dataclass
class QueryBatchResult:
    points: List[ScoredPoint] = field(default_factory=list)  

    # Optional diagnostics 
    ranking: str = None  # "rrf", "dbsf", "max_score", ...
    per_query: Optional[List[List[ScoredPoint]]] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return (
            f"QueryBatchResult("
            f"retrieved points: {len(self.points)}, "
            f"ranking strategy: {self.ranking}, "
            f"{self.meta})"
        )

    def __iter__(self):
        return iter(self.points)



@dataclass(frozen=True)
class HttpClient:
    """
    TODO:
    - initialize without a base_url. always require full url.
    - proper construction of the requests.
    """
    base_url: str
    timeout: Tuple[float, float] = REQUEST_TIMEOUT
    api_key: Optional[str] = None

    def post(self, 
             path: str, 
             payload: Dict[str, Any], 
             headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:

        url = self.base_url + path
        log.info(f"HTTP POST {url}")
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            r.raise_for_status()
        except requests.HTTPError as e:
            resp = e.response

            log.error(f"HTTP POST {url} failed"
                      f"status_code: {resp.status_code if resp else None}"
                      f"reason: {resp.reason if resp else None}"
                      f"response_body: {resp.text}",
                      exc_info=True
                      )
        
        return r.json()
    
    def get(self):
        pass

    def put(self):
        pass


class LLMProvider(Protocol):
    def embed(self, inputs: Sequence[str]) -> List[List[float]]:
        ...

    def generate(self, prompt: str, *, options: Optional[Dict[str, Any]] = None) -> str:
        ...

    def chat(self, messages: List[Dict[str, str]], *, options: Optional[Dict[str, Any]] = None) -> str:
        ...
    
    @property
    def models(self):
        ...

class OllamaProvider:
    """
    TODO:
    - initialize without model. require model always as input.
    - initialize only with url. Do not require a client object. httpclient is to be called
    """
    def __init__(self, http: HttpClient, 
                 model: Optional[str] = None):
        
        self.http = http
        self.model = model

    def embed(self, inputs: Sequence[str], options: Dict[str, Any] | None = None, model: str | None = None) -> str:
        j = self.http.post("/api/embed", {"model": model or self.model, "input": list(inputs), "options": options, "truncate": True})
        return j.get("embeddings") or []

    def generate(self, prompt: str, *, options=None, model: str | None = None) -> str:
        log.info(model)
        payload = {"model": model or self.model, "prompt": prompt, "options": options, "stream": False}
        j = self.http.post("/api/generate", payload)
        return (j.get("response") or "").strip()
    
    def chat(self, messages, *, options=None, model: str | None = None) -> str:
        payload = {"model": model or self.mmodel, "messages": messages, "options": options, "stream": False}
        j = self.http.post("/api/chat", payload)
        return (j.get("response") or "").strip()

    @property
    def models(self):
        j = self.http.post("/api/tags", timeout=REQUEST_TIMEOUT)
        return list[j.get("models", [])]


class Embedder:
    """
    TODO:
    - pass through options.
    """
    def __init__(self, provider: LLMProvider, model=DEFAULT_EMBEDDING_MODEL):
        self.provider = provider
        self.default_model = model

    def embed(self, data: str, model: str | None = None, options: Optional[dict] = None):
        vecs = self.provider.embed([data] if isinstance(data, str) else data, model=model or self.default_model)
        return vecs if vecs else None


class Generator:
    def __init__(self, provider: LLMProvider, model = DEFAULT_GEN_MODEL):
        self.provider = provider
        self.default_model = model

    def generate(self, prompt: str, options: Optional[dict] = None, model: str | None = None) -> str:
        response = self.provider.generate(prompt, options=options, model=model or self.default_model)
        return response


class Reranker:
    """
    TODO:
    - include score_threshold to return only list with scores over threshold after reranking
    - actually pass through options.
    """
    def __init__(self, provider: LLMProvider, model=DEFAULT_RERANKER_MODEL):
        self.provider = provider
        self.default_model = model

    def _score_pair(self, prompt: str, model: str | None = None) -> float:

        options= {"temperature": 0, "num_predict": 3, "raw": True}
        response  = self.provider.generate(prompt, 
                                           options=options, 
                                           model=model or self.default_model)
        text = response.lower()
        if text.startswith("yes"): return 1.0
        if text.startswith("no"):  return 0.0
        return 0.5

    def _build_prompt(self, instruction: str, query: str, doc_text: str) -> str:
        # Mirrors the format used in Qwen's model card examples (yes/no decision)
        return (
            "<|im_start|>system\n"
            "Judge whether the Document meets the requirements based on the Query provided. "
            "Note that the answer can only be \"yes\" or \"no\"."
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"<Instruct>: {instruction}\n"
            f"<Query>: {query}\n"
            f"<Document>: {doc_text}\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n<think>\n\n</think>\n\n"
        )

    DEFAULT_INSTRUCT = "For an enterprise ISMS, retrieve relevant passages that answer the query."

    def rerank(self, query: str, points, instruction=DEFAULT_INSTRUCT, max_workers=4, options=None):
        
        jobs = {}
        scores: dict = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for c in points:
                doc_text = c.payload.get("content", "")
                prompt = self._build_prompt(instruction, query, doc_text)
                jobs[pool.submit(self._score_pair, prompt)] = c.id

            for fut in as_completed(jobs):
                cid = jobs[fut]
                try:
                    scores[cid] = float(fut.result())
                except Exception:
                    scores[cid] = 0.0  # robust fallback

        for c in points:
            init_score = c.score
            c.score = 0.2* init_score + 0.8 * scores.get(c.id, 0.0)
        filtered_points = [c for c in points if c.score >= 0.5]
        filtered_points.sort(key=lambda x: x.score, reverse=True)
        return filtered_points


class DBProvider(Protocol):
    def initialize(self, collection: str, config: Dict[str, Any] = DEFAULT_CONFIG) -> None:
        ...
    def upsert(self, collection:str, points: List[Dict[str, Any]]) -> None:
        ...
    def query(self):
        ...
    def query_batch(self):
        ...

class QdrantDB(DBProvider):

    def __init__(self, http: HttpClient):
        self.http = http
        self.client = QdrantClient(url=http.base_url)

    def get_collections(self):
        return self.client.get_collections()

    def _create_uuid(self) -> str:
        return str(uuid.uuid4())

    def initialize(self, config: Dict[str, Any] = DEFAULT_CONFIG) -> None:
        if not self.client.collection_exists(collection_name=collection):
            
            log.info(f"Collection '{collection}' not found → creating new collection.")

            vectors_config_dict = {}
            for vector_field, params in config["vectors"].items():
                vectors_config_dict[vector_field] = VectorParams(size=params["size"], distance=params["distance"])

            self.client.create_collection(
                collection_name=collection, 
                vectors_config=vectors_config_dict
            )

    def upsert(self, points: List[Dict[str, Any]], collection) -> None:
        
        if not isinstance(points, list):
            points = [points]

        log.info(f"Upserting {len(points)} points.")

        point_structs: List[PointStruct] = []
        for p in points:
            pid = p.get("id") or self._create_uuid()
            vectors = p.get("vectors")
            if vectors is None:
                raise ValueError("Each point must include 'vectors'.")

            payload = p.get("payload") or {}
            point_structs.append(PointStruct(id=pid, vector=vectors, payload=payload))

        self.client.upsert(
            collection_name=collection,
            wait=True,
            points=point_structs,
        )

    def query(self, 
              collection: str,
              embedding: List[float], 
              using: str = "Default", 
              limit: int = 5,
              offset: int = 0,
              with_payload: bool = True,
              with_vectors: bool = False,
              score_threshold: Optional[float] = 0.2,
              **kwargs
              ) -> List[ScoredPoint]:
        

        query_result = self.client.query_points(
                                          collection_name=collection, 
                                          query=embedding,
                                          using=using,
                                          score_threshold=score_threshold,
                                          limit=limit,
                                          offset=offset,
                                          with_payload=with_payload,
                                          with_vectors=with_vectors,
                                          **kwargs
                                          )

        pts = list(query_result.points or [])
        pts.sort(key=lambda x: (x.score is None, x.score), reverse=True)

        return pts
    
    
    def query_batch(
            self,
            collection: str, 
            embeddings: List[List[float]],
            ranking: Ranking = "rrf",
            using: str = "Default",
            limit: int = 5,
            offset: int = 0,
            prefetch_limit: Optional[int] = None,
            with_payload: bool = True,
            with_vectors: bool = False,
            score_threshold: Optional[float] = None,
            **kwargs
        ) -> QueryBatchResult:

        
        if not embeddings:
            return QueryBatchResult(per_query=[])
        """
        if len(embeddings) == 1:
            per_query = [
                self.query(
                    collection=collection,
                    embedding=emb,
                    using=using,
                    limit=limit,
                    offset=offset,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold,
                    **kwargs,
                )
                for emb in embeddings
            ]
            flat = list(itertools.chain.from_iterable(per_query))
            return QueryBatchResult(
                        points=flat,
                        ranking=None,
                        per_query=per_query,
                        meta={"collection": collection,
                              "embeddings": len(embeddings), 
                              "using": using,
                              "limit": limit,
                              "offset": offset,
                              "score_threshold": score_threshold},
                    )
        """
        if ranking.lower() not in _ALLOWED_RANKINGS:
            log.warning(f"Unknown ranking strategy: '{ranking}'. Resorting to 'rrf'.")
            ranking = "rrf"

        if ranking.lower() in ("rrf", "dbsf"):
            prefetch_limit = prefetch_limit or max(limit + offset, 20)

            prefetch = [
                models.Prefetch(
                    query=emb,
                    using=using,
                    limit=prefetch_limit,
                )
                for emb in embeddings
            ]

            fusion = models.Fusion.RRF if ranking == "rrf" else models.Fusion.DBSF

            res = self.client.query_points(
                collection_name=collection,
                prefetch=prefetch,
                query=models.FusionQuery(fusion=fusion),
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors,
                score_threshold=score_threshold,
                **kwargs,
            )

            # qdrant-client returns an object with `.points`
            pts = list(res.points or [])
            # Already ranked server-side, but safe to normalize ordering
            pts.sort(key=lambda x: (x.score is None, x.score), reverse=True)
            
            return QueryBatchResult(
                        points=pts,
                        ranking=ranking,
                        per_query=None,  # intentionally omitted (would require extra calls)
                        meta={
                            "collection": collection,
                            "embeddings": len(embeddings),
                            "using": using,
                            "prefetch_limit": prefetch_limit,
                            "limit": limit,
                            "offset": offset,
                            "score_threshold": score_threshold,
                        },
                    )


        if ranking.lower() == "max_score":
            # change behaviour to use Qdrant.query_batch_points
            per_query = [
                self.query(
                    collection=collection,
                    embedding=emb,
                    using=using,
                    score_threshold=score_threshold,
                    limit=limit,
                    offset=offset,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    **kwargs,
                )
                for emb in embeddings
            ]
            seen: Dict[Any, ScoredPoint] = {}
            for p in itertools.chain.from_iterable(results):
                if p.id not in seen or (p.score is not None and p.score > seen[p.id].score):
                    seen[p.id] = p
            merged = sorted(seen.values(), key=lambda p: (p.score is None, p.score), reverse=True)

            return QueryBatchResult(
                    points=merged[:limit],
                    ranking=ranking,
                    per_query=per_query,
                    meta={
                        "collection": collection,
                        "embeddings": len(embeddings), 
                        "using": using,
                        "limit": limit,
                        "offset": offset,
                        "score_threshold": score_threshold},
                )

class Retriever:
    def __init__(self, provider: DBProvider):
        self.provider = provider
    
    def retrieve_test(self, query_request: Dict[str, Any]) -> List:
        """ 
        assuming query_request is a dict, generate QueryRequest and forward 
        to the DBprovider that accepts these QueryRequests. Like this Retriever
        remains agnostic to the actual DB used.
        TODO: 
        - Improve variable names to be more intuitive.
        """
        query = QueryRequest.from_schema(query_request)
        result = self.provider.query_batch(query)
       
        return result.points
    
    def retrieve(self, collection: str, embeddings, options: Optional[Dict[str, Any]] = None) -> List:
        query_opts = options
        result = self.provider.query_batch(
            collection=collection, 
            embeddings=embeddings, 
            using = query_opts.using,
            ranking=query_opts.ranking,
            limit = query_opts.limit,
            offset = query_opts.offset,
            prefetch_limit=query_opts.prefetch_limit,
            with_payload = query_opts.with_payload,
            with_vectors = query_opts.with_vectors,
            score_threshold=query_opts.score_threshold,
            )
        return result.points
    

class Constructor:    
    """
    TODO:
    - dynamic setting of domain. currently hard coded...
    """
    # --- Prompts ---
    SIMPLE_PROMPT = "Represent this sentence for searching relevant passages: {query}"
    Q2E_PROMPT = "Expand the query '{query}' into 3 search-friendly versions using synonyms and \
            related terms. Prioritize technical terms from {domain}. \
            Only return the generated questions with \n as delimiter."
    
    HyDE_PROMPT = "Write a hypothetical short paragraph answering {query}. Prioritize technical terms from {domain}.\
            Only return the generated paragraph."

    def construct(self, query : str, mode: Mode, options) -> QueryPlan:
        
        llm_schema = options.get("llm", {})
        query_schema = options.get("query", {})

        if not llm_schema or not query_schema:
            raise logger.hestIAError("No schemas provided. Exit method.")

        if mode == "simple":
            """
            Plan:
            1. get SIMPLE_PROMPT
            2. embed simple_prompt
            3. search db with embedding (require search params)
            4. post-process, e.g., rerank
            5. generate response
            """
            prompt = self.SIMPLE_PROMPT.format(query=query)
            steps=[
                QueryStep(type="PASS_THROUGH", payload=prompt, flow=STEP_DEFS["PASS_THROUGH"].flow),
                QueryStep(type="EMBED", options=llm_schema.get("emb"), flow=STEP_DEFS["EMBED"].flow),
                QueryStep(type="VECTOR_SEARCH", options=query_schema, flow=STEP_DEFS["VECTOR_SEARCH"].flow),
                ]
            
            rerank_schema = llm_schema.get("rrk")
            if rerank_schema:
                steps.append(QueryStep(type="RERANK", options=rerank_schema, flow=STEP_DEFS["RERANK"].flow))

            return QueryPlan(query, mode=mode, steps=steps)
                             
        
        if mode == "q2e":
            """
            Plan:
            1. Get Q2E_PROMPT with the user prompt.
            2. Send to LLM to generate multiple expanded questions
            3. Embed each question and search the DB
            4. Consolidate retrieved set (erase duplicates)
            5. post-process, e.g., rerank
            6. generate response
            """
            prompt = self.Q2E_PROMPT.format(query=query, domain="ISMS")
            steps=[
                QueryStep(type="LLM_GENERATE", payload=prompt, flow=STEP_DEFS["LLM_GENERATE"].flow),
                QueryStep(type="EMBED", options=llm_schema.get("emb"), flow=STEP_DEFS["EMBED"].flow),
                QueryStep(type="VECTOR_SEARCH", options=query_schema, flow=STEP_DEFS["VECTOR_SEARCH"].flow),
            ]
            rerank_schema = llm_schema.get("rrk")
            if rerank_schema:
                steps.append(QueryStep(type="RERANK", options=rerank_schema, flow=STEP_DEFS["RERANK"].flow))
            return QueryPlan(query, mode="q2e", steps=steps)

        if mode == "hyDE":
            """
            Plan:
            1. get HyDE_Prompt with the user prompt.
            2. Send to LLM to generate hypothetical document.
            3. Embed hypothetical document and search the DB
            4. Post-process, e.g., rerank
            5. generate response
            """
            prompt = self.HyDE_PROMPT.format(query=query, domain="ISMS")

            steps=[
                QueryStep(type="LLM_GENERATE", payload=prompt, flow=STEP_DEFS["LLM_GENERATE"].flow),
                QueryStep(type="EMBED", options=llm_schema.get("emb"), flow=STEP_DEFS["EMBED"].flow),
                QueryStep(type="VECTOR_SEARCH", options=query_schema, flow=STEP_DEFS["VECTOR_SEARCH"].flow),
            ]
            rerank_schema = llm_schema.get("rrk")
            if rerank_schema:
                steps.append(QueryStep(type="RERANK", options=rerank_schema, flow=STEP_DEFS["RERANK"].flow))

            return QueryPlan(query, mode=mode, steps=steps)

        if mode == "hybrid":
            """
            Plan:
            1. 
            
            """
            pass

        if mode == "extract":
            prompt = self.SIMPLE_PROMPT.format(query=query)
            steps=[
                QueryStep(type="PASS_THROUGH", payload=prompt, flow=STEP_DEFS["PASS_THROUGH"].flow),
                QueryStep(type="EMBED", options=llm_schema.get("emb"), flow=STEP_DEFS["EMBED"].flow),
                QueryStep(type="VECTOR_SEARCH", options=query_schema, flow=STEP_DEFS["VECTOR_SEARCH"].flow),
                ]
            
            return QueryPlan(query, mode=mode, steps=steps)

        log.warning(f"Unsupported mode: {mode}")

    def resolve(self, req: Request, exec: ExecutionContext) -> QueryPlan:
 
        if isinstance(req, RAGRequest):
            mode = req.mode
            query = req.query
            collection = req.collection

            if mode == "simple":
                prompt = self.SIMPLE_PROMPT.format(query=query)
                steps=[
                    QueryStep(type="PASS_THROUGH", payload=prompt, flow=STEP_DEFS["PASS_THROUGH"].flow),
                    QueryStep(type="EMBED", options=exec.emb, flow=STEP_DEFS["EMBED"].flow),
                    QueryStep(type="VECTOR_SEARCH", payload=collection, 
                              options=exec.query, flow=STEP_DEFS["VECTOR_SEARCH"].flow),
                    ]

            if mode == "hyDE":
                prompt = self.HyDE_PROMPT.format(query=query, domain="ISMS")
                steps=[
                    QueryStep(type="LLM_GENERATE", payload=prompt, flow=STEP_DEFS["LLM_GENERATE"].flow),
                    QueryStep(type="EMBED", options=exec.emb, flow=STEP_DEFS["EMBED"].flow),
                    QueryStep(type="VECTOR_SEARCH", payload=collection,
                              options=exec.query, flow=STEP_DEFS["VECTOR_SEARCH"].flow),
                    ]

            if mode == "q2e":
                prompt = self.Q2E_PROMPT.format(query=query, domain="ISMS")
                steps=[
                    QueryStep(type="LLM_GENERATE", payload=prompt, flow=STEP_DEFS["LLM_GENERATE"].flow),
                    QueryStep(type="EMBED", options=exec.emb, flow=STEP_DEFS["EMBED"].flow),
                    QueryStep(type="VECTOR_SEARCH", payload=collection,
                              options=exec.query, flow=STEP_DEFS["VECTOR_SEARCH"].flow),
                    ]
            if exec.rrk:
                steps.append(QueryStep(type="RERANK", options=exec.rrk, flow=STEP_DEFS["RERANK"].flow))

            return QueryPlan(query, mode=mode, steps=steps)
        
        log.warning(f"Unsupported request type: {req.type}")

class Router:

    def __init__(self, endpoints: dict[str, Any]):
        self.endpoints = endpoints

    def _validate_flow_step(self, step: QueryStep, ctx: QueryContext) -> bool:
        
        if not step.flow:
            return False

        for required in step.flow.requires:
            if getattr(ctx, required, None) is None:
                log.warning(f"Step '{step.type}' requires '{required}' "
                            f"but it is missing from context.")
                return False
        return True
        
    def _dispatch(self, step: QueryStep, ctx: QueryContext):
        method = STEP_DEFS[step.type].method

        if method is None:
            if step.type == "PASS_THROUGH":
                ctx.queries = [step.payload]
            return

        endpoint = self.endpoints.get(method)
        if not endpoint:
            raise RuntimeError(f"No endpoint registered for {method}")

        if step.type == "LLM_GENERATE":
            ctx.queries = endpoint.generate(
                step.payload,
                options=step.options
            ).splitlines()

        elif step.type == "EMBED":
            ctx.embeddings = endpoint.embed(
                ctx.queries,
                options=step.options
            )

        elif step.type == "RERANK":
            ctx.points = endpoint.rerank(
                ctx.org_query,
                ctx.points,
                options=step.options
            )

        elif step.type == "VECTOR_SEARCH":
            ctx.points = endpoint.retrieve(
                collection=step.payload,
                embeddings=ctx.embeddings,
                options=step.options
            )

    def route(self, plan: QueryPlan) -> QueryContext:
        
        plan.validate()
        ctx = QueryContext(org_query=plan.query)

        for step in plan.steps:
            self._validate_flow_step(step, ctx)
            self._dispatch(step, ctx)

        return ctx


class RequestHandler:
    def __init__(self, defaults: dict = settings.DEFAULT_EXECUTION_CONTEXT):
        self.defaults = defaults


    def _merge_execution(self, execution: dict) -> dict:
        """
        Merge execution overrides onto defaults.
        """
        merged = deepcopy(self.defaults)

        for section in ("llm", "emb", "rrk", "query"):
            if section in execution:
                merged[section] = _deep_merge(
                    merged.get(section, {}),
                    execution[section],
                )

        return merged


    def handle(self, raw_request: dict) -> Request:
        """
        Normalize *any* incoming request (CLI, API, UI).
        Expected raw:
            {
            "type": str "query, rag",
            "body":
                "query": message,
                "collection": collection,
                "mode": mode,

            # optional advanced inputs
            "execution": {
                "query_options": dict
                "llm": dict,
            }
        }

        """
        request_type = raw_request["type"]
        body = raw_request["body"]
        
        if request_type == "query":
            request = QueryRequest.from_schema({
                "type": "query",
                **body,
            })

        elif request_type == "rag":
            request = RAGRequest.from_schema({
                "type": "rag",
                **body,
            })

        
        else:
            raise ValueError("Unknown request type")
    
        execution = raw_request.get("execution", {})
        exec_cfg = self._merge_execution(execution)

        ctx = ExecutionContext(
            llm=LLMConfig.from_dict(exec_cfg["llm"]),
            emb=EmbConfig.from_dict(exec_cfg["emb"]),
            rrk=LLMConfig.from_dict(exec_cfg["rrk"]),
            query=QueryOptions.from_dict(exec_cfg["query"]),
        )

        return request, ctx

        

if __name__ == "__main__":
    
    # initialize endpoints
    ollama_url = HttpClient(LLM_URL)
    qdrant_url = HttpClient(DB_URL)

    ollama = OllamaProvider(ollama_url)
    qdrant = QdrantDB(qdrant_url)

    # Initialize whatever you want to call it
    generator = Generator(ollama, model=DEFAULT_GEN_MODEL)
    embedder = Embedder(ollama, model=DEFAULT_EMBEDDING_MODEL)
    reranker = Reranker(ollama, model=DEFAULT_RERANKER_MODEL)
    
    retriever = Retriever(qdrant)

    # Set endpoints
    endpoints = {
        "generate": generator,
        "embed": embedder,
        "rerank": reranker,
        "retrieve": retriever
    }

    query = "Suggest a password that complies with itrust's policy."

    collection = "itrust ISMS"

    llm_settings = {
        "gen": {"model": DEFAULT_GEN_MODEL, },
        "emb": {"model": DEFAULT_EMBEDDING_MODEL, "vector_size": 1024},
        "rrk": {"model": DEFAULT_RERANKER_MODEL, "temperature": 0, "num_predict": 3, "raw": True},
    }

    gen = LLMConfig(DEFAULT_GEN_MODEL)
    emb = EmbConfig(DEFAULT_EMBEDDING_MODEL)
    rrk = LLMConfig(DEFAULT_RERANKER_MODEL, temperature=0, num_predict=3, raw=True)

    db_settings = {
        "query": {
            "using": "Default",
            "limit": 5,
            "offset": 0,
            "score_threshold": 0.2,
            "with_payload": True,
            "with_vectors": False,
            "filter": None
            },
        "upsert": {
            "collection": collection,
            "vectors": None,
            },
        "init": {
            "collection": collection,
            "vectors": {
                "name": "Default",
                "size": 1024,
                "distance": "Cosine"
            },
            "sparse_vectors": {},
        }
    }

    router = Router(endpoints)
    query_opts = QueryOptions().from_schema(db_settings["query"])
    options = {"llm": llm_settings, 
               "query": query_opts}
    request = RAGRequest(type="rag", query=query, mode="simple", collection=collection)


    exec = ExecutionContext(llm=gen, emb=emb, rrk=rrk, query=query_opts)
    #qplan = QueryConstructor().construct(query=query, mode="q2e", options=options)
    qplan = Constructor().resolve(request, exec)
    results = router.route(qplan)