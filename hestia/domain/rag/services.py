from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Literal, Optional, Union, overload

import Stemmer

from hestia.domain.exceptions import ConfigurationError, NotFoundError
from hestia.domain.rag.types import DenseVector, Query, SparseVector
from hestia.infrastructure.db.protocol import DBProvider
from hestia.infrastructure.llm.protocol import LLMProvider

Message = Dict[str, str]

_log = logging.getLogger("hestia.system")


class Generator:

    def __init__(self, provider: LLMProvider, model: str = ""):
        self.provider = provider
        self.default_model = model

    @overload
    def generate(self, prompt: str, *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[False] = False) -> str: ...
    @overload
    def generate(self, prompt: str, *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[True]) -> Iterator[str]: ...

    def generate(self, prompt: str, *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: bool = False):
        _m = model or self.default_model
        _log.debug("generator_generate", extra={"model": _m, "prompt_len": len(prompt), "stream": stream})
        return self.provider.generate(prompt, model=_m, options=options, stream=stream)

    @overload
    def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[False] = False) -> str: ...
    @overload
    def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[True]) -> Iterator[str]: ...

    def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: bool = False):
        _m = model or self.default_model
        _log.debug("generator_chat", extra={"model": _m, "n_messages": len(messages), "stream": stream})
        return self.provider.chat(messages, model=_m, options=options, stream=stream)


class DenseEncoder:

    def __init__(self, provider: LLMProvider, model: str = ""):
        self.provider = provider
        self.default_model = model

    def encode(self, inputs: str | List[str], model: str | None = None, options: Optional[Dict[str, Any]] = None) -> DenseVector:
        inputs = [inputs] if isinstance(inputs, str) else inputs
        _m = model or self.default_model
        _log.debug("dense_encode", extra={"model": _m, "n_inputs": len(inputs)})
        resp = self.provider.embed(inputs, model=_m, options=options)
        vec = DenseVector(vector=resp[0])
        _log.debug("dense_encode_done", extra={"model": _m, "vector_dim": len(vec.vector)})
        return vec

    def encode_batch(self, inputs: List[str], model: str | None = None, options: Optional[Dict[str, Any]] = None) -> List[DenseVector]:
        _m = model or self.default_model
        _log.debug("dense_encode_batch", extra={"model": _m, "n_inputs": len(inputs)})
        resp = self.provider.embed(inputs, model=_m, options=options)
        vecs = [DenseVector(vector=emb) for emb in resp]
        _log.debug("dense_encode_batch_done", extra={"model": _m, "n_vectors": len(vecs), "vector_dim": len(vecs[0].vector) if vecs else 0})
        return vecs


@dataclass
class _CorpusStats:
    vocab: Dict[str, int]
    N: int            # total chunk count
    total_tokens: int # sum of all chunk lengths — avgdl = total_tokens / N
    df: Dict[int, int] = field(default_factory=dict)  # token_id → document frequency
    k1: float = 1.5
    b: float = 0.75
    language: str = "english"

    @property
    def avgdl(self) -> float:
        return max(self.total_tokens / max(self.N, 1), 1.0)

    def idf(self, tid: int) -> float:
        dfi = self.df.get(tid, 0)
        return math.log(1.0 + (self.N - dfi + 0.5) / (dfi + 0.5))


@dataclass
class _DocStats:
    """Per-document contribution to the corpus — stored on disk only, never cached."""
    n_chunks: int
    total_tokens: int
    df: Dict[int, int]  # token_id → number of chunks in this doc containing that token


class SparseEncoder:

    TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_./-]+")

    def __init__(self, corpus_dir: Path):
        corpus_dir = Path(corpus_dir)
        corpus_dir.mkdir(parents=True, exist_ok=True)
        self.corpus_dir = corpus_dir
        self._cache: Dict[str, _CorpusStats] = {}
        self._lock = threading.Lock()

    def _cache_key(self, corpus_name: str) -> str:
        return corpus_name.strip().replace(" ", "_")

    # ------------------------------------------------------------------
    # Corpus I/O
    # ------------------------------------------------------------------

    def _corpus_path(self, corpus_name: str) -> Path:
        return self.corpus_dir / (corpus_name.strip().replace(" ", "_") + ".json")

    def _load(self, corpus_name: str) -> _CorpusStats:
        path = self._corpus_path(corpus_name)
        if not path.exists():
            raise NotFoundError(f"Corpus '{corpus_name}' not found at {path}")
        with open(path, "r") as f:
            d = json.load(f)
        return _CorpusStats(
            vocab=d.get("vocab", {}),
            N=d.get("N", 0),
            total_tokens=d.get("total_tokens", 0),
            df={int(k): v for k, v in d.get("df", {}).items()},
            language=d.get("language", "english"),
        )

    def _load_or_empty(self, corpus_name: str) -> _CorpusStats:
        path = self._corpus_path(corpus_name)
        if not path.exists():
            return _CorpusStats(vocab={}, N=0, total_tokens=0)
        return self._load(corpus_name)

    def _save(self, corpus_name: str, stats: _CorpusStats,
              doc_stats: Dict[str, "_DocStats"]) -> None:
        path = self._corpus_path(corpus_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "vocab": stats.vocab,
                "N": stats.N,
                "total_tokens": stats.total_tokens,
                "df": {str(k): v for k, v in stats.df.items()},
                "language": stats.language,
                "doc_stats": {
                    uri: {
                        "n_chunks": ds.n_chunks,
                        "total_tokens": ds.total_tokens,
                        "df": {str(k): v for k, v in ds.df.items()},
                    }
                    for uri, ds in doc_stats.items()
                },
            }, f)

    def _load_full(self, corpus_name: str) -> tuple[_CorpusStats, Dict[str, _DocStats]]:
        """Read corpus file returning (global stats, per-doc stats).
        Used only on the deletion path — never populates the cache."""
        path = self._corpus_path(corpus_name)
        if not path.exists():
            return _CorpusStats(vocab={}, N=0, total_tokens=0), {}
        with open(path, "r") as f:
            d = json.load(f)
        stats = _CorpusStats(
            vocab=d.get("vocab", {}),
            N=d.get("N", 0),
            total_tokens=d.get("total_tokens", 0),
            df={int(k): v for k, v in d.get("df", {}).items()},
            language=d.get("language", "english"),
        )
        doc_stats = {
            uri: _DocStats(
                n_chunks=v["n_chunks"],
                total_tokens=v["total_tokens"],
                df={int(k): cnt for k, cnt in v["df"].items()},
            )
            for uri, v in d.get("doc_stats", {}).items()
        }
        return stats, doc_stats

    def _get_stats(self, corpus_name: str) -> _CorpusStats:
        """Return stats from in-memory cache, loading from disk on first access.
        Returns empty stats if no corpus file exists yet (e.g. empty collection)."""
        key = self._cache_key(corpus_name)
        with self._lock:
            if key not in self._cache:
                self._cache[key] = self._load_or_empty(corpus_name)
            return self._cache[key]

    def delete_corpus(self, corpus_name: str) -> None:
        """Delete the corpus file and evict the in-memory cache entry."""
        with self._lock:
            path = self._corpus_path(corpus_name)
            path.unlink(missing_ok=True)
            self._cache.pop(self._cache_key(corpus_name), None)
        _log.info("corpus_deleted", extra={"corpus": corpus_name})

    def remove_document(self, source_uri: str, corpus_name: str) -> None:
        """Subtract one document's contribution from the corpus and update the cache.

        Reads the full corpus file (global + doc_stats), performs the subtraction,
        writes back, then caches only the updated global stats — memory profile unchanged.
        Vocab token IDs are intentionally preserved even when df reaches zero so that
        existing Qdrant sparse vectors remain valid.
        """
        with self._lock:
            stats, doc_stats = self._load_full(corpus_name)

            ds = doc_stats.pop(source_uri, None)
            if ds is None:
                _log.warning("corpus_remove_doc_not_found",
                             extra={"corpus": corpus_name, "source_uri": source_uri})
                return

            new_df = dict(stats.df)
            for tid, count in ds.df.items():
                new_df[tid] = new_df.get(tid, 0) - count
            new_df = {tid: cnt for tid, cnt in new_df.items() if cnt > 0}

            updated = _CorpusStats(
                vocab=stats.vocab,
                N=max(stats.N - ds.n_chunks, 0),
                total_tokens=max(stats.total_tokens - ds.total_tokens, 0),
                df=new_df,
                language=stats.language,
            )
            self._save(corpus_name, updated, doc_stats)
            self._cache[self._cache_key(corpus_name)] = updated

        _log.info("corpus_document_removed",
                  extra={"corpus": corpus_name, "source_uri": source_uri})

    def preload_all(self) -> None:
        """Load all corpus files from disk into the in-memory cache at startup."""
        for path in sorted(self.corpus_dir.glob("*.json")):
            try:
                self._cache[path.stem] = self._load(path.stem)
                _log.info("sparse_encoder_preloaded", extra={"corpus": path.stem})
            except Exception:
                _log.warning("sparse_encoder_preload_failed", extra={"corpus": path.stem})

    # ------------------------------------------------------------------
    # Tokenisation
    # ------------------------------------------------------------------

    def _tokenize(self, texts: Union[str, List[str]], stemmer: Optional[Stemmer.Stemmer] = None):
        """Build a fresh local vocab from texts. Used for query-time encoding."""
        if isinstance(texts, str):
            texts = [texts]
        vocab: Dict[str, int] = {}
        ids_per_text: List[List[int]] = []
        next_id = 0
        for text in texts:
            tokens = self.TOKEN_RE.findall(text.lower())
            if stemmer:
                tokens = [stemmer.stemWord(t) for t in tokens]
            text_ids: List[int] = []
            for tok in tokens:
                if tok not in vocab:
                    vocab[tok] = next_id
                    next_id += 1
                text_ids.append(vocab[tok])
            ids_per_text.append(text_ids)
        return ids_per_text, vocab

    def _tokenize_extend(self, texts: List[str], vocab: Dict[str, int],
                         stemmer: Stemmer.Stemmer) -> List[List[int]]:
        """Tokenize texts while extending an existing vocab in-place."""
        next_id = (max(vocab.values()) + 1) if vocab else 0
        ids_per_text: List[List[int]] = []
        for text in texts:
            tokens = self.TOKEN_RE.findall(text.lower())
            tokens = [stemmer.stemWord(t) for t in tokens]
            ids: List[int] = []
            for tok in tokens:
                if tok not in vocab:
                    vocab[tok] = next_id
                    next_id += 1
                ids.append(vocab[tok])
            ids_per_text.append(ids)
        return ids_per_text

    # ------------------------------------------------------------------
    # Vector builders
    # ------------------------------------------------------------------

    def _build_query_vector(self, data: str, stats: _CorpusStats,
                            stemmer: Stemmer.Stemmer) -> SparseVector:
        """IDF-only vector for query-time encoding."""
        _, t_vocab = self._tokenize(data, stemmer)
        pairs = sorted(
            ((stats.vocab[tok], stats.idf(stats.vocab[tok])) for tok in t_vocab if tok in stats.vocab),
            key=lambda x: x[0],
        )
        indices, values = (list(t) for t in zip(*pairs)) if pairs else ([], [])
        return SparseVector(indices=indices, values=values)

    def _build_document_vectors(self, new_indices: List[List[int]],
                                stats: _CorpusStats) -> List[SparseVector]:
        """Full BM25 TF-IDF vectors for index-time document encoding."""
        vecs: List[SparseVector] = []
        for ids in new_indices:
            if not ids:
                vecs.append(SparseVector(indices=[], values=[]))
                continue
            tf = Counter(ids)
            dl = len(ids)
            pairs = sorted(
                (
                    (tid, stats.idf(tid) * (f * (stats.k1 + 1.0))
                     / (f + stats.k1 * (1.0 - stats.b + stats.b * dl / stats.avgdl)))
                    for tid, f in tf.items()
                ),
                key=lambda x: x[0],
            )
            indices, values = zip(*pairs) if pairs else ([], [])
            vecs.append(SparseVector(indices=list(indices), values=list(values)))
        return vecs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode(self, data: str, corpus_name: str) -> SparseVector:
        """Query-time: IDF-only encoding. Stats served from in-memory cache."""
        _log.debug("sparse_encode", extra={"corpus": corpus_name, "input_len": len(data)})
        stats = self._get_stats(corpus_name)
        stemmer = Stemmer.Stemmer(stats.language)
        vec = self._build_query_vector(data, stats, stemmer)
        _log.debug("sparse_encode_done", extra={"corpus": corpus_name, "nnz": len(vec.indices)})
        return vec

    def encode_documents(self, texts: List[str], corpus_name: str,
                         source_uri: str = "", language: str = "english") -> List[SparseVector]:
        """Index-time: extend corpus, return BM25 TF-IDF vectors, update cache.

        ``language`` is only applied when creating a new corpus (N == 0).
        Existing corpora keep their language so that vocabulary remains consistent.
        """
        _log.debug("sparse_encode_docs", extra={"corpus": corpus_name, "n_texts": len(texts)})

        with self._lock:
            stats, doc_stats = self._load_full(corpus_name)

            lang = stats.language if stats.N > 0 else language
            stemmer = Stemmer.Stemmer(lang)
            new_indices = self._tokenize_extend(texts, stats.vocab, stemmer)

            new_df = dict(stats.df)
            this_doc_df: Dict[int, int] = {}
            for chunk_ids in new_indices:
                for tid in set(chunk_ids):
                    new_df[tid] = new_df.get(tid, 0) + 1
                    this_doc_df[tid] = this_doc_df.get(tid, 0) + 1

            if source_uri:
                doc_stats[source_uri] = _DocStats(
                    n_chunks=len(new_indices),
                    total_tokens=sum(len(ids) for ids in new_indices),
                    df=this_doc_df,
                )

            updated = _CorpusStats(
                vocab=stats.vocab,
                N=stats.N + len(new_indices),
                total_tokens=stats.total_tokens + sum(len(ids) for ids in new_indices),
                df=new_df,
                language=lang,
            )
            self._save(corpus_name, updated, doc_stats)
            self._cache[self._cache_key(corpus_name)] = updated  # global stats only — doc_stats stays on disk

        vecs = self._build_document_vectors(new_indices, updated)
        _log.debug("sparse_encode_docs_done", extra={
            "corpus": corpus_name, "vocab_size": len(updated.vocab),
            "N": updated.N, "new_chunks": len(new_indices),
        })
        return vecs


class Retriever:

    def __init__(self, provider: DBProvider):
        self.provider = provider

    def retrieve(self, collection: str, query: Query, options: Dict[str, Any] = None):
        _log.debug("retriever_query", extra={"collection": collection, "query_type": type(query).__name__})
        result = self.provider.search(collection, query, options=options)
        n_hits = len(result.points) if hasattr(result, "points") else 0
        _log.debug("retriever_done", extra={"collection": collection, "n_hits": n_hits})
        return result
