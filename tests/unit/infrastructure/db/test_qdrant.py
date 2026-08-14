from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import httpx
import pytest
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from hestia.domain.exceptions import ProviderError
from hestia.infrastructure.db.qdrant import QdrantDB, _retry_on_transient_error
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
# __init__ — HTTP keep-alive disabled (avoids reusing a pooled connection a
# remote reverse proxy has already silently killed, surfacing as WinError
# 10054 only once reused)
# ---------------------------------------------------------------------------

class TestInit:

    def test_disables_keepalive_on_client_construction(self, mock_client):
        with patch("hestia.infrastructure.db.qdrant.QdrantClient", return_value=mock_client) as MockClient:
            QdrantDB(http="https://qdrant.itrust.lu:6333")
        limits = MockClient.call_args.kwargs["limits"]
        assert isinstance(limits, httpx.Limits)
        assert limits.max_keepalive_connections == 0


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

    def test_retries_and_recovers_from_stale_connection(self, db, mock_client, monkeypatch):
        # A stale pooled connection to Qdrant (e.g. the peer closing an idle
        # keep-alive connection) surfaces as ResponseHandlingException --
        # this must be retried transparently, not crash the search.
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        mock_client.query_points.side_effect = [
            ResponseHandlingException(ConnectionResetError("reset")),
            MagicMock(points=[]),
        ]
        query = DenseVector(vector=[0.1, 0.2])
        result = db.search("col", query)
        assert result.points == []
        assert mock_client.query_points.call_count == 2

    def test_raises_provider_error_when_connection_never_recovers(self, db, mock_client, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        mock_client.query_points.side_effect = ResponseHandlingException(ConnectionResetError("reset"))
        query = DenseVector(vector=[0.1, 0.2])
        with pytest.raises(ProviderError):
            db.search("col", query)


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
# bump_classification
# ---------------------------------------------------------------------------

class TestBumpClassification:

    def test_sets_when_no_current_value(self, db, mock_client):
        point = MagicMock(payload={"access": {}})
        mock_client.scroll.return_value = ([point], None)

        db.bump_classification("col", "doc.pdf", 3)

        mock_client.set_payload.assert_called_once()
        kwargs = mock_client.set_payload.call_args.kwargs
        assert kwargs["payload"] == {"access": {"classification": 3}}

    def test_sets_when_requested_higher_than_current(self, db, mock_client):
        point = MagicMock(payload={"access": {"classification": 1}})
        mock_client.scroll.return_value = ([point], None)

        db.bump_classification("col", "doc.pdf", 3)

        mock_client.set_payload.assert_called_once()

    def test_noop_when_current_already_at_or_above_requested(self, db, mock_client):
        point = MagicMock(payload={"access": {"classification": 3}})
        mock_client.scroll.return_value = ([point], None)

        db.bump_classification("col", "doc.pdf", 1)

        mock_client.set_payload.assert_not_called()

    def test_noop_when_document_not_found(self, db, mock_client):
        mock_client.scroll.return_value = ([], None)

        db.bump_classification("col", "doc.pdf", 3)

        mock_client.set_payload.assert_not_called()


# ---------------------------------------------------------------------------
# get_classifications
# ---------------------------------------------------------------------------

class TestGetClassifications:

    def test_empty_source_uris_returns_empty_without_querying(self, db, mock_client):
        assert db.get_classifications("col", []) == {}
        mock_client.scroll.assert_not_called()

    def test_finds_classification_for_each_uri_in_one_page(self, db, mock_client):
        points = [
            MagicMock(payload={"source_uri": "a.pdf", "access": {"classification": 1}}),
            MagicMock(payload={"source_uri": "b.pdf", "access": {"classification": 3}}),
        ]
        mock_client.scroll.return_value = (points, None)

        result = db.get_classifications("col", ["a.pdf", "b.pdf"])

        assert result == {"a.pdf": 1, "b.pdf": 3}
        mock_client.scroll.assert_called_once()

    def test_ignores_points_not_in_requested_set(self, db, mock_client):
        points = [
            MagicMock(payload={"source_uri": "other.pdf", "access": {"classification": 4}}),
            MagicMock(payload={"source_uri": "a.pdf", "access": {"classification": 1}}),
        ]
        mock_client.scroll.return_value = (points, None)

        result = db.get_classifications("col", ["a.pdf"])

        assert result == {"a.pdf": 1}

    def test_stops_early_once_all_uris_found(self, db, mock_client):
        points = [MagicMock(payload={"source_uri": "a.pdf", "access": {"classification": 0}})]
        mock_client.scroll.return_value = (points, "some-next-offset")

        result = db.get_classifications("col", ["a.pdf"])

        assert result == {"a.pdf": 0}
        mock_client.scroll.assert_called_once()

    def test_paginates_until_all_found_or_exhausted(self, db, mock_client):
        page1 = ([MagicMock(payload={"source_uri": "a.pdf", "access": {"classification": 2}})], "offset-2")
        page2 = ([MagicMock(payload={"source_uri": "b.pdf", "access": {"classification": 3}})], None)
        mock_client.scroll.side_effect = [page1, page2]

        result = db.get_classifications("col", ["a.pdf", "b.pdf"])

        assert result == {"a.pdf": 2, "b.pdf": 3}
        assert mock_client.scroll.call_count == 2

    def test_missing_uri_after_exhausted_scroll_is_simply_absent(self, db, mock_client):
        mock_client.scroll.return_value = ([], None)

        result = db.get_classifications("col", ["missing.pdf"])

        assert result == {}


# ---------------------------------------------------------------------------
# rename_source
# ---------------------------------------------------------------------------

class TestRenameSource:

    def test_calls_set_payload_with_new_source_uri(self, db, mock_client):
        db.rename_source("col", "old/doc.pdf", "new/doc.pdf")

        mock_client.set_payload.assert_called_once()
        kwargs = mock_client.set_payload.call_args.kwargs
        assert kwargs["payload"] == {"source_uri": "new/doc.pdf"}


# ---------------------------------------------------------------------------
# get_document
# ---------------------------------------------------------------------------

class TestGetDocument:

    def test_returns_none_when_document_not_found(self, db, mock_client):
        mock_client.scroll.return_value = ([], None)

        assert db.get_document("col", "missing.pdf") is None

    def test_returns_doc_info_and_ordered_chunks(self, db, mock_client):
        def _point(pid, position, content, header="H"):
            p = MagicMock()
            p.id = pid
            p.payload = {
                "id": pid,
                "doc_info": {"title": "T"},
                "info": {"header": header, "path": header, "level": 1, "position": position},
                "content": content,
                "token_count": 5,
            }
            return p

        mock_client.scroll.return_value = (
            [_point("c2", 10, "second"), _point("c1", 0, "first")], None
        )

        result = db.get_document("col", "doc.pdf")

        assert result["doc_info"] == {"title": "T"}
        assert [c["id"] for c in result["chunks"]] == ["c1", "c2"]
        assert result["chunks"][0]["content"] == "first"

    def test_paginates_across_scroll_pages(self, db, mock_client):
        def _point(pid, position):
            p = MagicMock()
            p.id = pid
            p.payload = {
                "id": pid, "doc_info": {}, "info": {"position": position}, "content": "x", "token_count": 1,
            }
            return p

        mock_client.scroll.side_effect = [
            ([_point("a", 0)], "offset-2"),
            ([_point("b", 1)], None),
        ]

        result = db.get_document("col", "doc.pdf")

        assert [c["id"] for c in result["chunks"]] == ["a", "b"]
        assert mock_client.scroll.call_count == 2


# ---------------------------------------------------------------------------
# update_document_metadata
# ---------------------------------------------------------------------------

class TestUpdateDocumentMetadata:

    def test_returns_false_when_document_not_found(self, db, mock_client):
        mock_client.scroll.return_value = ([], None)

        result = db.update_document_metadata("col", "missing.pdf", {"title": "New"}, 1)

        assert result is False
        mock_client.set_payload.assert_not_called()

    def test_new_payload_replaces_existing_non_reserved_fields(self, db, mock_client):
        point = MagicMock(payload={"doc_info": {"title": "Old", "document_id": "org-doc", "author": "A"}})
        mock_client.scroll.return_value = ([point], None)

        result = db.update_document_metadata("col", "doc.pdf", {"title": "New"}, 2)

        assert result is True
        mock_client.set_payload.assert_called_once()
        kwargs = mock_client.set_payload.call_args.kwargs
        assert kwargs["payload"]["doc_info"] == {"title": "New", "document_id": "org-doc"}
        assert kwargs["payload"]["access"] == {"classification": 2}

    def test_preserves_document_id_when_client_omits_it(self, db, mock_client):
        point = MagicMock(payload={"doc_info": {"document_id": "org-doc"}})
        mock_client.scroll.return_value = ([point], None)

        db.update_document_metadata("col", "doc.pdf", {"title": "New"}, None)

        kwargs = mock_client.set_payload.call_args.kwargs
        assert kwargs["payload"]["doc_info"]["document_id"] == "org-doc"
        assert kwargs["payload"]["access"] == {"classification": None}

    def test_drops_custom_key_omitted_from_new_payload(self, db, mock_client):
        point = MagicMock(payload={
            "doc_info": {"title": "Old", "document_id": "org-doc", "custom_key": "value"},
        })
        mock_client.scroll.return_value = ([point], None)

        db.update_document_metadata("col", "doc.pdf", {"title": "New"}, 1)

        kwargs = mock_client.set_payload.call_args.kwargs
        assert kwargs["payload"]["doc_info"] == {"title": "New", "document_id": "org-doc"}

    def test_preserves_chunking_strategy_when_omitted(self, db, mock_client):
        point = MagicMock(payload={
            "doc_info": {"document_id": "org-doc", "chunking_strategy": "block"},
        })
        mock_client.scroll.return_value = ([point], None)

        db.update_document_metadata("col", "doc.pdf", {"title": "New"}, 1)

        kwargs = mock_client.set_payload.call_args.kwargs
        assert kwargs["payload"]["doc_info"]["chunking_strategy"] == "block"

    def test_new_custom_key_is_kept(self, db, mock_client):
        point = MagicMock(payload={"doc_info": {"title": "Old", "document_id": "org-doc"}})
        mock_client.scroll.return_value = ([point], None)

        db.update_document_metadata("col", "doc.pdf", {"title": "New", "added_key": "v"}, 1)

        kwargs = mock_client.set_payload.call_args.kwargs
        assert kwargs["payload"]["doc_info"] == {"title": "New", "document_id": "org-doc", "added_key": "v"}


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
# collections
# ---------------------------------------------------------------------------

class TestCollections:

    def test_lists_collections_with_point_counts(self, db, mock_client):
        mock_client.get_collections.return_value = MagicMock(
            collections=[_collection_desc("a"), _collection_desc("b")]
        )
        mock_client.get_collection.return_value = MagicMock(points_count=5, status=MagicMock(value="green"))
        result = db.collections
        assert [c["name"] for c in result["collections"]] == ["a", "b"]

    def test_raises_provider_error_when_qdrant_unreachable(self, db, mock_client, monkeypatch):
        # e.g. Qdrant's container is down / DNS resolution fails -- must not
        # let a raw transport exception escape and crash the ASGI app.
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        mock_client.get_collections.side_effect = ResponseHandlingException(OSError("getaddrinfo failed"))
        with pytest.raises(ProviderError):
            _ = db.collections


# ---------------------------------------------------------------------------
# get_collection — deduplication
# ---------------------------------------------------------------------------

class TestGetCollection:

    def test_returns_none_when_collection_not_found(self, db, mock_client):
        mock_client.collection_exists.return_value = False
        result = db.get_collection("missing")
        assert result is None

    def test_raises_provider_error_when_qdrant_unreachable(self, db, mock_client, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        mock_client.collection_exists.side_effect = ResponseHandlingException(OSError("getaddrinfo failed"))
        with pytest.raises(ProviderError):
            db.get_collection("col")

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

    def test_raises_provider_error_when_qdrant_unreachable(self, db, mock_client, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        mock_client.get_collections.side_effect = ResponseHandlingException(OSError("getaddrinfo failed"))
        with pytest.raises(ProviderError):
            db.document_counts()

    def test_scrolls_once_per_collection_sequentially(self, db, mock_client):
        mock_client.get_collections.return_value = MagicMock(
            collections=[_collection_desc("x"), _collection_desc("y"), _collection_desc("z")]
        )
        mock_client.scroll.return_value = ([], None)
        db.document_counts()
        # one scroll call per collection -- no internal fan-out/concurrency
        assert mock_client.scroll.call_count == 3


# ---------------------------------------------------------------------------
# _retry_on_transient_error
# ---------------------------------------------------------------------------

class TestRetryOnTransientError:

    def test_returns_result_on_success(self):
        fn = MagicMock(return_value="ok")
        assert _retry_on_transient_error(fn) == "ok"
        fn.assert_called_once()

    def test_raises_immediately_on_non_429(self):
        err = UnexpectedResponse(status_code=500, reason_phrase="Error", content=b"", headers={})
        fn = MagicMock(side_effect=err)
        with pytest.raises(UnexpectedResponse):
            _retry_on_transient_error(fn)
        fn.assert_called_once()

    def test_retries_then_succeeds_on_429(self, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        err = UnexpectedResponse(status_code=429, reason_phrase="Too Many Requests", content=b"", headers={})
        fn = MagicMock(side_effect=[err, "ok"])
        assert _retry_on_transient_error(fn) == "ok"
        assert fn.call_count == 2

    def test_raises_after_exhausting_attempts(self, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        err = UnexpectedResponse(status_code=429, reason_phrase="Too Many Requests", content=b"", headers={})
        fn = MagicMock(side_effect=err)
        with pytest.raises(UnexpectedResponse):
            _retry_on_transient_error(fn, max_attempts=3)

    def test_retries_then_succeeds_on_stale_connection(self, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        err = ResponseHandlingException(ConnectionResetError("reset"))
        fn = MagicMock(side_effect=[err, "ok"])
        assert _retry_on_transient_error(fn) == "ok"
        assert fn.call_count == 2

    def test_raises_after_exhausting_attempts_on_stale_connection(self, monkeypatch):
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        err = ResponseHandlingException(ConnectionResetError("reset"))
        fn = MagicMock(side_effect=err)
        with pytest.raises(ResponseHandlingException):
            _retry_on_transient_error(fn, max_attempts=3)

    def test_default_max_attempts_is_two(self, monkeypatch):
        # A deterministic failure (e.g. a client-side path/MTU problem) never
        # recovers on a 3rd or 4th try -- keep the default low so a doomed
        # call doesn't make the user wait tens of extra seconds for nothing.
        monkeypatch.setattr("hestia.infrastructure.db.qdrant.time.sleep", lambda *_: None)
        err = ResponseHandlingException(ConnectionResetError("reset"))
        fn = MagicMock(side_effect=err)
        with pytest.raises(ResponseHandlingException):
            _retry_on_transient_error(fn)
        assert fn.call_count == 2
