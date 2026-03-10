from typing import Optional, Dict, List, Any, Union, Optional, Iterator

from hestia.services import Embedder, Retriever, Generator
from hestia.schemas.api import HybridQuery, DenseVector, SparseVector
from hestia.settings import Settings as s


# =================== HELPRS TO BE REMOVED LATER ==================
from collections import Counter
import math
import Stemmer
import re
import json

with open("./app/data/corpus_index.json", "r") as file:
    corpus_tokens = json.load(file)
    file.close()

def compute_bm25_stats(token_ids_per_doc, k1=1.5, b=0.75):
    N = len(token_ids_per_doc)
    doc_lens = [len(ids) for ids in token_ids_per_doc]
    avgdl = max(sum(doc_lens) / max(N, 1), 1.0)

    df = Counter()
    for ids in token_ids_per_doc:
        df.update(set(ids))

    def idf(tid: int) -> float:
        dfi = df.get(tid, 0)
        return math.log(1.0 + (N - dfi + 0.5) / (dfi + 0.5))

    return {"N": N, "avgdl": avgdl, "df": df, "idf": idf, "k1": k1, "b": b}


CORPUSE_STATS = compute_bm25_stats(corpus_tokens.get("indices"))
CORPUS_VOCAB = corpus_tokens.get("vocab")


TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_./-]+")
def _default_tokenize(query: str) -> list[str]:
    return TOKEN_RE.findall(query.lower())

def tokenize(texts: Union[str, List[str]],
             stemmer: Optional[Stemmer.Stemmer] = None):
    
    if isinstance(texts, str):
        texts = [texts]

    vocab = {}
    ids_per_text = []
    next_id = 0
    for text in texts:
        tokens = _default_tokenize(text)
        if stemmer is not None:
            tokens = [stemmer.stemWord(t) for t in tokens]
        
        text_ids: List[int] =  []
        for tok in tokens:
            if tok in vocab:
                text_ids.append(vocab[tok])
            else:
                vocab[tok] = next_id
                text_ids.append(next_id)
                next_id += 1

        ids_per_text.append(text_ids)

    return ids_per_text, vocab

def build_sparse_query_vector(
        text: str, 
        vocab: dict[str, int], 
        stats: dict, 
        stemmer: Optional[Stemmer.Stemmer] = Stemmer.Stemmer("english")) -> SparseVector:
    """
    Create Qdrant SparseVector (indices, values) for sparse (keyword) search.
    Map query vocab to corpus vocab and retrieve corpus token ids with their
    idf weights. 
    """
    _, t_vocab = tokenize(text, stemmer)
    
    indices = []
    values = []
    
    for tok in t_vocab:
        tid = vocab.get(tok)
        if tid is None:
            continue
        dfi = stats["idf"](int(tid))
        
        indices.append(int(tid))
        values.append(dfi)

    pairs = sorted(zip(indices, values), key=lambda x: x[0])
    indices, values = (list(t) for t in zip(*pairs)) if pairs else ([], [])
    return SparseVector(indices=indices, values=values)
# =================================================================

class RAGenerator:

    SYSTEM_PROMPT = """
        You are an assistant with access to a knowledge base of Markdown documents. 
        Below are the most relevant excerpts retrieved from that database.
        <retrieved-data>
            {retrieved_data}
        </retrieved-data>
        Instruction:
        - Using only the retrieved data above, answer the user's question. 
        - If the retrieved data is insufficient, say so explicitly.
        - After generating your response, always:
            1. Explicitly list the sources used in the format:
            Sources:
            - [SOURCE]
            2. Append all retrieved articles in an expandable <details> section, formatted as:
            <details>
            <summary><b>Show retrieved articles</b></summary>
            <ul>
                <li><strong>[SOURCE: <TAG>]</strong></li>
                <li>Source content</li>
            </ul>
            </details>


        <user-prompt>
            {user_message}
        </user-prompt>
    """

    def __init__(self, embedder: Embedder, retriever: Retriever, generator: Generator):
        self.embedder = embedder
        self.retriever = retriever
        self.generator = generator

    def _get_collection_corpus(self, collection: str):
        # this should be moved to utils/common
        _map = {"ITR ISMS": s.CORPUS_INDEX}
        with open(_map[collection], "r") as file:
            corpus = json.load(file)
            file.close()
        return corpus
    
    def _build_augmented_prompt(self, message:str, retrieved_data: List[str]) -> str:
        return self.SYSTEM_PROMPT.format(
            retrieved_data=retrieved_data, 
            user_message=message
        )

    def _encode_dense(self, 
                      text: str | List[str], 
                      model: str = None, 
                      options: Dict[str, Any] = None
                      ) -> DenseVector:
        return DenseVector(vector=self.embedder.embed(text, model=model, options=options)[0])
    
    def _encode_sparse(self, 
                       text: str | List[str],
                       corpus: Dict[str, Any]
                       ) -> SparseVector:
        stats = compute_bm25_stats(corpus.get("indices"))
        vocab = corpus.get("vocab")
        return build_sparse_query_vector(text=text, vocab=vocab, stats=stats)
    
    def _retrieve_data(self, collection: str, query: str, options: Dict[str, Any] = None) -> List[str]:
        dense = self._encode_dense(query)
        corpus = self._get_collection_corpus(collection)
        sparse = self._encode_sparse(query, corpus)
        query = HybridQuery(dense=dense, sparse=sparse)
        res =  self.retriever.retrieve(collection, query, options=options)
        # make variable, for now just fix it.
        return res.points[:10]

    def generate(self, collection: str, message: str, options: Dict[str, Any] = None, stream: bool = False):
        _retrieve_data = self._retrieve_data(collection=collection, query=message, options=options)
        augmented_prompt = self._build_augmented_prompt(message=message, retrieved_data=_retrieve_data)
        return self.generator.generate(prompt=augmented_prompt, stream=stream)