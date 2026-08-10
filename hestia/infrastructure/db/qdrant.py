from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict

import httpx
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from hestia.domain.exceptions import ProviderError
from hestia.domain.rag.types import DenseVector, HybridQuery, Query, SparseVector
from hestia.infrastructure.db.protocol import DBProvider

_log = logging.getLogger("hestia.system")


def _retry_on_transient_error(fn: Callable, *args, max_attempts: int = 2, base_delay: float = 0.5, **kwargs):
    """Retries on transient, recoverable failures: Qdrant returning 429 under
    load, or a stale/reset pooled connection (ResponseHandlingException
    wrapping a raw socket error, e.g. the peer closing an idle keep-alive
    connection) -- both are expected conditions worth retrying on a fresh
    connection, unlike a genuine 4xx/5xx from Qdrant itself. Kept low (2, not
    the previous 4): a deterministic failure (e.g. a client-side path/MTU
    problem where the request body itself never gets through) doesn't get
    better on the 3rd or 4th try, so extra attempts just add tens of seconds
    of user-facing wait for no benefit -- genuinely transient blips still
    recover within one retry."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except UnexpectedResponse as e:
            if e.status_code != 429 or attempt == max_attempts - 1:
                raise
            _log.warning("qdrant_rate_limited_retry", extra={"attempt": attempt})
            time.sleep(base_delay * (2 ** attempt))
        except ResponseHandlingException:
            if attempt == max_attempts - 1:
                raise
            _log.warning("qdrant_connection_retry", extra={"attempt": attempt})
            time.sleep(base_delay * (2 ** attempt))


def _qdrant_call(fn: Callable, *args, **kwargs):
    """Runs a Qdrant client call with the same retry as
    _retry_on_transient_error, and converts an exhausted connection failure
    (Qdrant unreachable -- DNS failure, connection refused, etc.) into a
    domain ProviderError. Without this, callers like the admin
    collection-list/detail endpoints see a raw httpx/qdrant transport
    exception escape uncaught, crashing the ASGI app instead of returning a
    clean HTTP error response."""
    try:
        return _retry_on_transient_error(fn, *args, **kwargs)
    except ResponseHandlingException as e:
        _log.warning("qdrant_call_failed", extra={"fn": getattr(fn, "__name__", str(fn))})
        raise ProviderError(f"Vector database request failed: {e.source}") from e


class QdrantDB(DBProvider):

    UPSERT_BATCH = 64  # points per request — keeps payload size manageable

    def __init__(self, http: str, timeout: float = 300.0, api_key: str | None = None):
        # qdrant-client disables HTTP keep-alive automatically for literal
        # localhost/127.0.0.1 deployments (its own comment: "may cause extra
        # delays" -- see qdrant_remote.py), but our deployment goes through a
        # remote reverse proxy (e.g. qdrant.itrust.lu), which never matches
        # that check. Without this, httpx pools/reuses connections that the
        # proxy can silently kill server-side, surfacing as a
        # ResponseHandlingException (WinError 10054) only once reused --
        # disabling keep-alive here applies the same workaround unconditionally.
        self.client = QdrantClient(
            url=http, timeout=timeout, api_key=api_key,
            limits=httpx.Limits(max_connections=None, max_keepalive_connections=0),
        )

    # @MRS-024, @MRS-093
    def initialize(self, collection: str, config: Dict[str, Any]) -> None:
        if self.client.collection_exists(collection_name=collection):
            return
        dense_dim = config.get("dense_dim", 1024)
        owner_org_id = config.get("owner_org_id")
        metadata = {"owner_org_id": owner_org_id} if owner_org_id is not None else None
        _log.info("qdrant_create_collection", extra={"collection": collection, "dense_dim": dense_dim})
        self.client.create_collection(
            collection_name=collection,
            vectors_config={
                "dense": models.VectorParams(size=dense_dim, distance=models.Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False),
                )
            },
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=200),
            optimizers_config=models.OptimizersConfigDiff(
                deleted_threshold=0.2,
                vacuum_min_vector_number=1000,
                memmap_threshold=200000,
                indexing_threshold=20000,
            ),
            metadata=metadata,
        )
        if config.get("create_indexes", True):
            self.client.create_payload_index(
                collection_name=collection,
                field_name="doc_info.document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=collection,
                field_name="access.classification",
                field_schema=models.PayloadSchemaType.INTEGER,
            )

    def update_collection_owner(self, collection: str, owner_org_id: int) -> None:
        self.client.update_collection(
            collection_name=collection,
            metadata={"owner_org_id": owner_org_id},
        )

    def upsert(self, collection: str, points: list[Dict[str, Any]]) -> None:
        qdrant_points = []
        for p in points:
            vectors: dict = {}
            if "dense" in p:
                vectors["dense"] = p["dense"]
            if "sparse" in p:
                sp = p["sparse"]
                vectors["sparse"] = models.SparseVector(indices=sp["indices"], values=sp["values"])
            qdrant_points.append(
                models.PointStruct(id=p["id"], payload=p["payload"], vector=vectors)
            )
        _log.debug("qdrant_upsert", extra={"collection": collection, "n_points": len(qdrant_points)})
        for i in range(0, len(qdrant_points), self.UPSERT_BATCH):
            batch = qdrant_points[i:i + self.UPSERT_BATCH]
            self.client.upsert(collection_name=collection, wait=True, points=batch)

    # @MRS-027
    def search(self, collection: str, query: Query, *, options: Dict[str, Any] = None):
        limit = 50
        with_payload = True
        with_vectors = False
        score_threshold = 0
        filter_ = None

        if options:
            limit = options.get("limit", 50)
            with_payload = options.get("with_payload", True)
            with_vectors = options.get("with_vectors", False)
            score_threshold = options.get("score_threshold", 0)
            filter_ = self._build_filter(options.get("filters"))

        query_type = type(query).__name__
        _log.debug("qdrant_search", extra={
            "collection": collection,
            "query_type": query_type,
            "limit": limit,
            "has_filter": filter_ is not None,
        })

        try:
            # @MRS-027
            if isinstance(query, HybridQuery):
                result = _retry_on_transient_error(
                    self.client.query_points,
                    collection_name=collection,
                    prefetch=[
                        models.Prefetch(
                            query=models.SparseVector(indices=query.sparse.indices, values=query.sparse.values),
                            using="sparse",
                            limit=200,
                            filter=filter_,
                        ),
                        models.Prefetch(
                            query=query.dense.vector,
                            using="dense",
                            limit=100,
                            filter=filter_,
                        ),
                    ],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=limit,
                    with_payload=True,
                )
            elif isinstance(query, SparseVector):
                result = _retry_on_transient_error(
                    self.client.query_points,
                    collection_name=collection,
                    query=models.SparseVector(indices=query.indices, values=query.values),
                    using="sparse",
                    limit=limit,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold,
                    query_filter=filter_,
                )
            # @MRS-030
            elif isinstance(query, DenseVector):
                result = _retry_on_transient_error(
                    self.client.query_points,
                    collection_name=collection,
                    query=query.vector,
                    using="dense",
                    limit=limit,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                    score_threshold=score_threshold,
                    query_filter=filter_,
                )
            else:
                raise TypeError(f"Unsupported query type: {type(query)}")
        except ResponseHandlingException as e:
            # Retries in _retry_on_transient_error are exhausted -- surface as
            # a domain error so callers (e.g. the chat stream) can degrade
            # gracefully instead of a raw connection error crashing the
            # response mid-stream.
            _log.warning("qdrant_search_failed", extra={"collection": collection})
            raise ProviderError(f"Vector search failed: {e.source}") from e

        n_hits = len(result.points) if hasattr(result, "points") else 0
        _log.debug("qdrant_search_done", extra={"collection": collection, "n_hits": n_hits})
        return result

    # @MRS-031
    def _build_filter(self, filter_opts: dict | None):
        if not filter_opts:
            return None
        max_cls = filter_opts.get("max_classification")
        if max_cls is None:
            return None
        return models.Filter(
            must=[models.FieldCondition(
                key="access.classification",
                range=models.Range(lte=max_cls),
            )]
        )

    def delete_collection(self, collection: str) -> bool:
        if not self.client.collection_exists(collection_name=collection):
            return False
        _log.info("qdrant_delete_collection", extra={"collection": collection})
        self.client.delete_collection(collection_name=collection)
        return True

    @property
    def collections(self) -> dict:
        descs = _qdrant_call(self.client.get_collections).collections
        result = []
        for c in descs:
            info = _qdrant_call(self.client.get_collection, collection_name=c.name)
            result.append({
                "id": c.name,
                "name": c.name,
                "points_count": info.points_count or 0,
                "status": info.status.value if hasattr(info.status, "value") else str(info.status),
            })
        return {"collections": result}

    def delete_document(self, collection: str, source_uri: str) -> None:
        self.client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source_uri",
                            match=models.MatchValue(value=source_uri),
                        )
                    ]
                )
            ),
            wait=True,
        )
        _log.info("qdrant_delete_document", extra={"collection": collection, "source_uri": source_uri})

    def _scroll_documents(self, collection: str) -> dict[str, dict]:
        """Scroll through all points, deduplicate by source_uri to build the
        document list. Fetch the full payload to avoid partial-selector
        quirks and to support points ingested before the top-level
        uploaded_by/uploaded_at fields were introduced (those values live in
        doc_info for older chunks)."""
        docs: dict[str, dict] = {}
        offset = None
        while True:
            results, next_offset = _qdrant_call(
                self.client.scroll,
                collection_name=collection,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in results:
                p = point.payload or {}
                doc_info = p.get("doc_info") or {}

                def _val(*keys: str) -> str:
                    """Return the first non-empty, non-'None' value found across payload paths."""
                    _JUNK = {"", "none", "null"}
                    for k in keys:
                        v = p.get(k) or doc_info.get(k)
                        s = str(v).strip() if v is not None else ""
                        if s.lower() not in _JUNK:
                            return s
                    return ""

                source      = _val("source")
                source_uri  = _val("source_uri") or source or doc_info.get("document_id", "") or "unknown"
                uploaded_by = _val("uploaded_by", "upserted_by")
                uploaded_at = _val("uploaded_at", "upserted_at")
                if source_uri not in docs:
                    docs[source_uri] = {
                        "source": source or source_uri,
                        "source_uri": source_uri,
                        "uploaded_by": uploaded_by,
                        "uploaded_at": uploaded_at,
                        "chunk_count": 1,
                    }
                else:
                    docs[source_uri]["chunk_count"] += 1
            if next_offset is None:
                break
            offset = next_offset
        return docs

    def get_collection(self, collection: str) -> dict | None:
        if not _qdrant_call(self.client.collection_exists, collection_name=collection):
            return None
        info = _qdrant_call(self.client.get_collection, collection_name=collection)
        docs = self._scroll_documents(collection)
        return {
            "name": collection,
            "points_count": info.points_count or 0,
            "status": info.status.value if hasattr(info.status, "value") else str(info.status),
            "documents": list(docs.values()),
        }

    def document_counts(self) -> dict[str, int]:
        """Document counts for every collection, computed sequentially (not
        in parallel) so this single call never itself becomes a burst of
        concurrent scroll requests against Qdrant."""
        descs = _qdrant_call(self.client.get_collections).collections
        return {c.name: len(self._scroll_documents(c.name)) for c in descs}
