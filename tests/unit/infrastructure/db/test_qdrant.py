from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest
from qdrant_client.http.exceptions import UnexpectedResponse

from hestia.infrastructure.db.qdrant import QdrantDB, _retry_on_rate_limit
from hestia.domain.rag.types import DenseVector, HybridQuery, SparseVector


# ---------------------------------------------------------------------------
# Fixture: QdrantDB with mocked client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def db(mock_client):
    with patch("hestia.infrastructure.db.qdrant.QdrantClient", return_value=mock_client):
        return QdrantDB(http="http://localhost:6333")


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------

class TestInitialize:

    def test_skips_when_collection_exists(self, db, mock_client):
        mock_client.collection_exists.return_value = True
        db.initialize("existing-col", {"dense_dim": 512})
        mock_client.create_collection.assert_not_called()

    def test_creates_collection_when_missing(self, db, mock_client):
        mock_client.collection_exists.return_value = False
        db.initialize("new-col", {"dense_dim": 512})
        mock_client.create_collection.assert_called_once()

    def test_dense_dim_passed_to_vector_config(self, db, mock_client):
        mock_client.collection_exists.return_value = False
        db.initialize("col", {"dense_dim": 768})
        call_kwargs = mock_client.create_collection.call_args.kwargs
        assert call_kwargs["vectors_config"]["dense"].size == 768

    def test_creates_payload_indexes_when_flag_set(self, db, mock_client):
        mock_client.collection_exists.return_value = False
        db.initialize("col", {"dense_dim": 512, "create_indexes": True})
        assert mock_client.create_payload_index.call_count == 2


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------

class TestUpsert:

    def test_calls_client_upsert(self, db, mock_client):
        points = [{
            "id": "abc123",
            "payload": {"content": "hello"},
            "dense": [0.1, 0.2],
            "sparse": {"indices": [0], "values": [0.5]},
        }]
        db.upsert("col", points)
        mock_client.upsert.assert_called()

    def test_batches_large_input(self, db, mock_client):
        points = [
            {"id": str(i), "payload": {}, "dense": [0.1], "sparse": {"indices": [0], "values": [0.1]}}
            for i in range(100)
        ]
        db.upsert("col", points)
        # UPSERT_BATCH=64 → expect 2 calls
        assert mock_client.upsert.call_count == 2


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:

    def test_dense_query_uses_query_points(self, db, mock_client):
        mock_client.query_points.return_value = MagicMock(points=[])
        mock_client.search.return_value = []
        query = DenseVector(vector=[0.1, 0.2])
        db.search("col", query)
        # DenseVector should use search or query_points
        assert mock_client.search.called or mock_client.query_points.called

    def test_hybrid_query_uses_prefetch(self, db, mock_client):
        mock_client.query_points.return_value = MagicMock(points=[])
        query = HybridQuery(
            dense=DenseVector(vector=[0.1, 0.2]),
            sparse=SparseVector(indices=[0], values=[0.5]),
        )
        db.search("col", query)
        mock_client.query_points.assert_called_once()

    def test_sparse_query_dispatched(self, db, mock_client):
        mock_client.search.return_value = []
        mock_client.query_points.return_value = MagicMock(points=[])
        query = SparseVector(indices=[0, 1], values=[0.5, 0.3])
        db.search("col", query)
        assert mock_client.search.called or mock_client.query_points.called


# ---------------------------------------------------------------------------
# delete_collection
# ---------------------------------------------------------------------------

class TestDeleteCollection:

    def test_returns_true_when_deleted(self, db, mock_client):
        mock_client.collection_exists.return_value = True
        result = db.delete_collection("col")
        assert result is True
        mock_client.delete_collection.assert_called_once_with(collection_name="col")

    def test_returns_false_when_not_found(self, db, mock_client):
        mock_client.collection_exists.return_value = False
        result = db.delete_collection("col")
        assert result is False
        mock_client.delete_collection.assert_not_called()


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------

class TestDeleteDocument:

    def test_calls_delete_with_filter(self, db, mock_client):
        db.delete_document("col", "doc://source.pdf")
        mock_client.delete.assert_called_once()


# ---------------------------------------------------------------------------
# _build_filter
# ---------------------------------------------------------------------------

class TestBuildFilter:

    def test_returns_none_when_no_opts(self, db):
        assert db._build_filter(None) is None
        assert db._build_filter({}) is None

    def test_returns_none_when_no_max_classification(self, db):
        assert db._build_filter({"limit": 10}) is None

    def test_returns_filter_with_classification_range(self, db):
        f = db._build_filter({"max_classification": 2})
        assert f is not None
        # Should have a FieldCondition on access.classification
        condition = f.must[0]
        assert condition.key == "access.classification"
        assert condition.range.lte == 2


# ---------------------------------------------------------------------------
# get_collection — deduplication
# ---------------------------------------------------------------------------

class TestGetCollection:

    def test_returns_none_when_collection_not_found(self, db, mock_client):
        mock_client.collection_exists.return_value = False
        result = db.get_collection("missing")
        assert result is None

    def test_deduplicates_points_by_source_uri(self, db, mock_client):
        mock_client.collection_exists.return_value = True
        mock_client.get_collection.return_value = MagicMock(
            points_count=3, status=MagicMock(value="green")
        )
        # Two chunks with the same source_uri, one with a different one
        def _point(source_uri, source="doc"):
            p = MagicMock()
            p.payload = {"source": source, "source_uri": source_uri, "doc_info": {}}
            return p

        mock_client.scroll.side_effect = [
            ([_point("a.pdf"), _point("a.pdf"), _point("b.pdf")], None),
        ]
        result = db.get_collection("col")
        assert len(result["documents"]) == 2
        uris = {d["source_uri"] for d in result["documents"]}
        assert uris == {"a.pdf", "b.pdf"}


# ---------------------------------------------------------------------------
# document_counts
# ---------------------------------------------------------------------------

def _collection_desc(name):
    m = MagicMock()
    m.name = name
    return m


def _point(source_uri):
    p = MagicMock()
    p.payload = {"source": "doc", "source_uri": source_uri, "doc_info": {}}
    return p


class TestDocumentCounts:

    def test_aggregates_counts_across_collections(self, db, mock_client):
        mock_client.get_collections.return_value = MagicMock(
            collections=[_collection_desc("col-a"), _collection_desc("col-b")]
        )
        mock_client.scroll.side_effect = [
            ([_point("a1"), _point("a2")], None),  # col-a: 2 distinct docs
            ([_point("b1")], None),                 # col-b: 1 distinct doc
        ]
        result = db.document_counts()
        assert result == {"col-a": 2, "col-b": 1}

    def test_scrolls_once_per_collection_sequentially(self, db, mock_client):
        mock_client.get_collections.return_value = MagicMock(
            collections=[_collection_desc("x"), _collection_desc("y"), _collection_desc("z")]
        )
        mock_client.scroll.return_value = ([], None)
        db.document_counts()
        # one scroll call per collection -- no internal fan-out/concurrency
        assert mock_client.scroll.call_count == 3


# ---------------------------------------------------------------------------
# _retry_on_rate_limit
# ---------------------------------------------------------------------------

class TestRetryOnRateLimit:

    def test_returns_result_on_success(self):
        fn = MagicMock(return_value="ok")
        assert _retry_on_rate_limit(fn) == "ok"
        fn.assert_called_once()

    def test_raises_immediately_on_non_429(self):
        err = UnexpectedResponse(status_code=500, reason_phrase="Error", content=b"", headers={})
        fn = MagicMock(side_effect=err)
        with pytest.raises(UnexpectedResponse):
            _retry_on_rate_limit(fn)
        fn.assert_called_once()

    def test_retries_then_succeeds_on_429(self, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        err = UnexpectedResponse(status_code=429, reason_phrase="Too Many Requests", content=b"", headers={})
        fn = MagicMock(side_effect=[err, "ok"])
        assert _retry_on_rate_limit(fn) == "ok"
        assert fn.call_count == 2

    def test_raises_after_exhausting_attempts(self, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        err = UnexpectedResponse(status_code=429, reason_phrase="Too Many Requests", content=b"", headers={})
        fn = MagicMock(side_effect=err)
        with pytest.raises(UnexpectedResponse):
            _retry_on_rate_limit(fn, max_attempts=3)
        assert fn.call_count == 3
