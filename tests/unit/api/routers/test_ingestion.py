from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.ingestion import router, _save_temp, _get_parser_direct
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from hestia.domain.auth.models import CollectionPermission
from hestia.domain.exceptions import ValidationError as DomainValidationError
from tests.unit.conftest import _make_user

import pytest


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


# ---------------------------------------------------------------------------
# _save_temp
# ---------------------------------------------------------------------------

class TestSaveTemp:

    def test_writes_bytes_and_returns_path(self):
        data = b"hello world"
        path = _save_temp(data, ".txt")
        try:
            content = Path(path).read_bytes()
            assert content == data
        finally:
            Path(path).unlink(missing_ok=True)

    def test_suffix_applied(self):
        path = _save_temp(b"x", ".pdf")
        try:
            assert path.endswith(".pdf")
        finally:
            Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# _get_parser_direct
# ---------------------------------------------------------------------------

class TestGetParserDirect:

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "file.xyz"
        with pytest.raises(DomainValidationError):
            _get_parser_direct(f, itrust_template=False)

    def test_txt_returns_txt_parser(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello world")
        from hestia.infrastructure.parsers.txt import TXTParser
        parser = _get_parser_direct(f, itrust_template=False)
        assert isinstance(parser, TXTParser)

    def test_docx_itr_returns_itr_parser(self, tmp_path):
        f = tmp_path / "file.docx"
        f.write_bytes(b"")
        # _get_parser_direct imports lazily inside the function body.
        # Patch the class on the source module so the `from ... import` inside
        # the function picks up the mock (Python resolves it from sys.modules).
        with patch("hestia.infrastructure.parsers.docx.ITRDOCXParser") as MockP:
            MockP.return_value = MagicMock()
            _get_parser_direct(f, itrust_template=True)
        MockP.assert_called_once()


# ---------------------------------------------------------------------------
# GET /collections (permission filtering)
# ---------------------------------------------------------------------------

class TestListCollections:

    def test_admin_gets_all(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(collections={"collections": [
                {"name": "col1"}, {"name": "col2"}
            ]})
        }
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections")
        assert resp.status_code == 200
        assert len(resp.json()["collections"]) == 2

    def test_user_filtered_to_permitted(self):
        user = _make_user(allowed_collections={
            "col1": CollectionPermission(access=True),
        })
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(collections={"collections": [
                {"name": "col1"}, {"name": "col2"}
            ]})
        }
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()["collections"]]
        assert "col1" in names
        assert "col2" not in names

    def test_wildcard_permission_returns_all(self):
        user = _make_user(allowed_collections={
            "*": CollectionPermission(access=True),
        })
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(collections={"collections": [
                {"name": "col1"}, {"name": "col2"}
            ]})
        }
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections")
        assert resp.status_code == 200
        assert len(resp.json()["collections"]) == 2


# ---------------------------------------------------------------------------
# GET /collections/document-counts
# ---------------------------------------------------------------------------

class TestGetDocumentCounts:

    def test_admin_gets_all(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(document_counts=MagicMock(return_value={"col1": 3, "col2": 5}))
        }
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/document-counts")
        assert resp.status_code == 200
        assert resp.json()["counts"] == {"col1": 3, "col2": 5}

    def test_user_filtered_to_permitted(self):
        user = _make_user(allowed_collections={
            "col1": CollectionPermission(access=True),
        })
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(document_counts=MagicMock(return_value={"col1": 3, "col2": 5}))
        }
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/document-counts")
        assert resp.status_code == 200
        assert resp.json()["counts"] == {"col1": 3}

    def test_route_registered_before_name_wildcard(self):
        # /collections/document-counts must resolve to this route, not be
        # swallowed by GET /collections/{name} matching name="document-counts"
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(
                document_counts=MagicMock(return_value={"col1": 1}),
                get_collection=MagicMock(return_value={"name": "document-counts", "documents": []}),
            )
        }
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/document-counts")
        assert resp.status_code == 200
        assert "counts" in resp.json()
        handler.container.providers["db"].get_collection.assert_not_called()


# ---------------------------------------------------------------------------
# GET /collections/{name}
# ---------------------------------------------------------------------------

class TestGetCollection:

    def test_returns_collection_with_documents(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(get_collection=MagicMock(return_value={
                "name": "col1",
                "documents": [
                    {"source_uri": "a.pdf"},
                    {"source_uri": "b.pdf"},
                ]
            }))
        }
        handler.container.services.get.return_value = None  # no users service
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/col1")
        assert resp.status_code == 200
        assert len(resp.json()["documents"]) == 2

    def test_returns_404_when_not_found(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.providers = {
            "db": MagicMock(get_collection=MagicMock(return_value=None))
        }
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/missing")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /parse
# ---------------------------------------------------------------------------

class TestParseDocument:

    def test_returns_metadata_and_markdown(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()

        from io import BytesIO
        client = TestClient(_app(user=user, handler=handler))

        mock_parser = MagicMock()
        mock_parser.get_metadata.return_value = {"source": "doc", "source_uri": "doc.txt"}
        mock_parser.to_markdown.return_value = "# Title\n\nContent"
        mock_parser.close.return_value = None

        with patch("hestia.api.routers.ingestion._get_parser_direct", return_value=mock_parser):
            resp = client.post(
                "/parse",
                data={"itrust_template": "false"},
                files={"file": ("doc.txt", BytesIO(b"hello world"), "text/plain")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "metadata" in data
        assert "markdown" in data


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

class TestUploadDocument:

    def test_calls_ingestion_pipeline(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.settings.classification_labels = []

        mock_pipeline = MagicMock()
        from hestia.application.ingestion import IngestionResult
        mock_pipeline.ingest.return_value = IngestionResult(
            collection="test-col", source="doc", n_chunks=3, n_upserted=3, elapsed_ms=100.0
        )
        handler.container.services.get.return_value = mock_pipeline

        # Mock collection moderator check
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {
            "owner": {"id": 1, "name": "org"},
            "access": [],
        }
        user_with_perm = _make_user(is_admin=True)

        from io import BytesIO
        client = TestClient(_app(user=user_with_perm, handler=handler))
        resp = client.post(
            "/upload",
            data={"collection": "test-col", "tenants": "[]"},
            files={"file": ("doc.txt", BytesIO(b"# Title\n\nBody"), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["n_chunks"] == 3
