from __future__ import annotations

import logging
from typing import Any, Dict

from qdrant_client import QdrantClient, models

from hestia.domain.rag.types import DenseVector, HybridQuery, Query, SparseVector
from hestia.infrastructure.db.protocol import DBProvider

_log = logging.getLogger("hestia.system")


class QdrantDB(DBProvider):

    UPSERT_BATCH = 64  # points per request — keeps payload size manageable

    def __init__(self, http: str, timeout: float = 300.0, api_key: str | None = None):
        self.client = QdrantClient(url=http, timeout=timeout, api_key=api_key)

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

        # @MRS-027
        if isinstance(query, HybridQuery):
            result = self.client.query_points(
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
            result = self.client.query_points(
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
            result = self.client.query_points(
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
        descs = self.client.get_collections().collections
        result = []
        for c in descs:
            info = self.client.get_collection(collection_name=c.name)
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

    def get_collection(self, collection: str) -> dict | None:
        if not self.client.collection_exists(collection_name=collection):
            return None
        info = self.client.get_collection(collection_name=collection)

        # Scroll through all points, deduplicate by source_uri to build the document list.
        # Fetch the full payload to avoid partial-selector quirks and to support points
        # ingested before the top-level uploaded_by/uploaded_at fields were introduced
        # (those values live in doc_info for older chunks).
        docs: dict[str, dict] = {}
        offset = None
        while True:
            results, next_offset = self.client.scroll(
                collection_name=collection,
                limit=256,
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

        return {
            "name": collection,
            "points_count": info.points_count or 0,
            "status": info.status.value if hasattr(info.status, "value") else str(info.status),
            "documents": list(docs.values()),
        }
