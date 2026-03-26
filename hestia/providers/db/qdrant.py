from typing import Dict, Any
from qdrant_client import QdrantClient, models

from hestia.protocols.db import DBProvider
from hestia.utils import HttpClient
from hestia.schemas.api import DenseVector, SparseVector, Query, HybridQuery



class QdrantDB(DBProvider):

    
    def __init__(self, http: HttpClient | str ):
        if isinstance(http, str):
            self.client = QdrantClient(url=http)
        else:
            self.client = QdrantClient(url=http.base_url)

    def _map_fusion(self, ranking: str):
        if ranking == "rrf":
            return models.Fusion.RRF
        if ranking == "dbsf":
            return models.Fusion.DBSF
        raise ValueError(f"Unknown ranking: {ranking}")
    
    def search(self, 
            collection: str, 
            query: Query,
            *,
            options: Dict[str, Any] = None):    

        # defaults
        limit = 50
        with_payload = True
        with_vectors= False
        score_threshold = 0
        if options: 
            limit = options.get("limit", 50)
            with_payload = options.get("with_payload", True)
            with_vectors = options.get("with_vectors", False)
            score_threshold = options.get("score_threshold")

        if isinstance(query, HybridQuery):
            return self.client.query_points(
                collection_name=collection,
                prefetch=[
                    models.Prefetch(
                            query=models.SparseVector(indices=query.sparse.indices,
                                                      values=query.sparse.values),
                            using="sparse",
                            limit=200,
                        ),
                    models.Prefetch(
                        query=query.dense.vector,
                        using="dense",
                        limit=100
                    )
                    ],
                    query=models.FusionQuery(
                        fusion=models.Fusion.RRF
                    ),
                    limit=limit,
                    with_payload=True
                    )
        
        if isinstance(query, SparseVector):
            return self.client.query_points(
                collection_name=collection,
                query=models.SparseVector(indices=query.indices,
                                          values=query.values),
                using="sparse",
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vectors,
                score_threshold=score_threshold
            )
        
        if isinstance(query, DenseVector):
            return self.client.query_points(
                collection_name=collection,
                query=query.vector,
                using="dense",
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vectors,
                score_threshold=score_threshold
            )
        
        raise TypeError(f"Unsupported query request: {type(query)}")
    
    @property
    def collections(self):
        # TODO: define CollectionResponse to capture collection name and accessibility
        available_collections = []
        coll_descriptions  = self.client.get_collections().collections
        for idx, coll in enumerate(coll_descriptions):
            available_collections.append({"id": idx, "name": coll.name})
        return {"collections": available_collections}

