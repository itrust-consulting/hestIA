from __future__ import annotations

import json
from unittest.mock import ANY, MagicMock, patch
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.ingestion import router, _save_temp, _get_parser_direct
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from hestia.domain.auth.models import CollectionPermission
from hestia.domain.exceptions import ValidationError as DomainValidationError
from hestia.domain.rag.classification import Classification
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
        handler.container.require_db_provider.return_value = MagicMock(collections={"collections": [
            {"name": "col1"}, {"name": "col2"}
        ]})
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections")
        assert resp.status_code == 200
        assert len(resp.json()["collections"]) == 2

    def test_user_filtered_to_permitted(self):
        user = _make_user(allowed_collections={
            "col1": CollectionPermission(access=True),
        })
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock(collections={"collections": [
            {"name": "col1"}, {"name": "col2"}
        ]})
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
        handler.container.require_db_provider.return_value = MagicMock(collections={"collections": [
            {"name": "col1"}, {"name": "col2"}
        ]})
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
        handler.container.require_db_provider.return_value = MagicMock(
            document_counts=MagicMock(return_value={"col1": 3, "col2": 5})
        )
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/document-counts")
        assert resp.status_code == 200
        assert resp.json()["counts"] == {"col1": 3, "col2": 5}

    def test_user_filtered_to_permitted(self):
        user = _make_user(allowed_collections={
            "col1": CollectionPermission(access=True),
        })
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock(
            document_counts=MagicMock(return_value={"col1": 3, "col2": 5})
        )
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/document-counts")
        assert resp.status_code == 200
        assert resp.json()["counts"] == {"col1": 3}

    def test_route_registered_before_name_wildcard(self):
        # /collections/document-counts must resolve to this route, not be
        # swallowed by GET /collections/{name} matching name="document-counts"
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock(
            document_counts=MagicMock(return_value={"col1": 1}),
            get_collection=MagicMock(return_value={"name": "document-counts", "documents": []}),
        )
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/document-counts")
        assert resp.status_code == 200
        assert "counts" in resp.json()
        handler.container.require_db_provider.return_value.get_collection.assert_not_called()


# ---------------------------------------------------------------------------
# GET /collections/{name}
# ---------------------------------------------------------------------------

class TestGetCollection:

    def test_returns_collection_with_documents(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock(get_collection=MagicMock(return_value={
            "name": "col1",
            "documents": [
                {"source_uri": "a.pdf"},
                {"source_uri": "b.pdf"},
            ]
        }))
        handler.container.services.get.return_value = None  # no users service
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/col1")
        assert resp.status_code == 200
        assert len(resp.json()["documents"]) == 2

    def test_returns_404_when_not_found(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock(get_collection=MagicMock(return_value=None))
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/missing")
        assert resp.status_code == 404

    def test_user_without_collection_access_gets_403(self):
        # Regression test: this endpoint previously returned the full
        # document listing to any authenticated user regardless of tenant
        # membership or collection ACL.
        user = _make_user(allowed_collections={
            "other-col": CollectionPermission(access=True),
        })
        handler = MagicMock()
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/col1")
        assert resp.status_code == 403
        handler.container.require_db_provider.return_value.get_collection.assert_not_called()

    def test_user_with_specific_access_gets_data(self):
        user = _make_user(allowed_collections={
            "col1": CollectionPermission(access=True),
        })
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock(get_collection=MagicMock(return_value={
            "name": "col1", "documents": [{"source_uri": "a.pdf"}],
        }))
        handler.container.services.get.return_value = None
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/col1")
        assert resp.status_code == 200
        assert len(resp.json()["documents"]) == 1

    def test_user_with_wildcard_access_gets_data(self):
        user = _make_user(allowed_collections={
            "*": CollectionPermission(access=True),
        })
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock(get_collection=MagicMock(return_value={
            "name": "col1", "documents": [],
        }))
        handler.container.services.get.return_value = None
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/col1")
        assert resp.status_code == 200


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

    def test_parse_failure_does_not_leak_traceback(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()

        from io import BytesIO
        client = TestClient(_app(user=user, handler=handler))

        mock_parser = MagicMock()
        mock_parser.get_metadata.side_effect = RuntimeError("boom: /internal/path/leak")
        mock_parser.close.return_value = None

        with patch("hestia.api.routers.ingestion._get_parser_direct", return_value=mock_parser):
            resp = client.post(
                "/parse",
                data={"itrust_template": "false"},
                files={"file": ("doc.txt", BytesIO(b"hello world"), "text/plain")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["parse_error"] == "boom: /internal/path/leak"
        assert "traceback" not in data


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
        handler.container.services["sync_manifest"].upsert_entry.assert_not_called()

    def test_records_sync_manifest_entry_when_sync_fields_present(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.settings.classification_labels = []

        mock_pipeline = MagicMock()
        from hestia.application.ingestion import IngestionResult
        mock_pipeline.ingest.return_value = IngestionResult(
            collection="test-col", source="doc", n_chunks=0, n_upserted=0, elapsed_ms=1.0
        )
        handler.container.services.get.return_value = mock_pipeline
        sync_manifest = MagicMock()
        sync_manifest.claim_owner.return_value = "sub/doc.md"  # this upload wins ownership
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        from io import BytesIO
        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/upload",
            data={
                "collection": "test-col", "tenants": "[]",
                "sync_id": "my-repo", "content_hash": "abc123",
            },
            files={"file": ("sub/doc.md", BytesIO(b"# Title\n\nBody"), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deduped"] is False
        assert data["n_chunks"] == 0
        mock_pipeline.ingest.assert_called_once()
        sync_manifest.upsert_entry.assert_called_once()
        args = sync_manifest.upsert_entry.call_args[0]
        assert args[0] == "test-col"
        assert args[1] == "my-repo"
        assert args[2] == "sub/doc.md"
        assert args[3] == "abc123"

    def test_skips_ingest_when_content_already_owned_elsewhere(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.settings.classification_labels = []

        mock_pipeline = MagicMock()
        handler.container.services.get.return_value = mock_pipeline
        sync_manifest = MagicMock()
        sync_manifest.claim_owner.return_value = "original/report.pdf"  # someone else already owns this hash
        db = MagicMock()
        handler.container.require_db_provider.return_value = db
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        from io import BytesIO
        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/upload",
            data={
                "collection": "test-col", "tenants": "[]",
                "sync_id": "my-repo", "content_hash": "abc123",
            },
            files={"file": ("copy/report.pdf", BytesIO(b"duplicate bytes"), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deduped"] is True
        assert data["duplicate_of"] == "original/report.pdf"
        assert data["n_chunks"] == 0
        mock_pipeline.ingest.assert_not_called()
        db.bump_classification.assert_not_called()
        sync_manifest.upsert_entry.assert_called_once_with("test-col", "my-repo", "copy/report.pdf", "abc123", ANY)

    def test_dedup_bumps_owner_classification_when_more_restrictive(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.settings.classification_labels = []

        mock_pipeline = MagicMock()
        handler.container.services.get.return_value = mock_pipeline
        sync_manifest = MagicMock()
        sync_manifest.claim_owner.return_value = "original/report.pdf"
        db = MagicMock()
        handler.container.require_db_provider.return_value = db
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        from io import BytesIO
        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/upload",
            data={
                "collection": "test-col", "tenants": "[]",
                "sync_id": "my-repo", "content_hash": "abc123",
                "metadata_overrides": json.dumps({"classification": "confidential"}),
            },
            files={"file": ("copy/report.pdf", BytesIO(b"duplicate bytes"), "application/pdf")},
        )
        assert resp.status_code == 200
        db.bump_classification.assert_called_once_with("test-col", "original/report.pdf", 3)

    def test_non_moderator_forbidden(self):
        # Regression test: assert_collection_moderator gates this route but
        # had no endpoint-level test proving a non-privileged caller is
        # actually denied.
        user = _make_user()  # no admin, no moderated tenants
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        handler.container.services.get.return_value = users_svc

        from io import BytesIO
        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/upload",
            data={"collection": "secret-col", "tenants": "[]"},
            files={"file": ("doc.txt", BytesIO(b"body"), "text/plain")},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /collections/{name}/documents
# ---------------------------------------------------------------------------

class TestDeleteDocument:

    def test_non_moderator_forbidden(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.request("DELETE", "/collections/test-col/documents", params={"source_uri": "sub/doc.md"})

        assert resp.status_code == 403

    def _client(self, sync_manifest):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock()
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()
        handler.container.services.get.return_value = None
        return TestClient(_app(user=user, handler=handler)), handler

    def test_untracked_document_deletes_normally(self):
        # No sync_manifest row at all (plain document, never hash-tracked).
        sync_manifest = MagicMock()
        sync_manifest.get_hash_for_source.return_value = None
        client, handler = self._client(sync_manifest)

        resp = client.request("DELETE", "/collections/test-col/documents", params={"source_uri": "sub/doc.md"})

        assert resp.status_code == 200
        handler.container.require_db_provider.return_value.delete_document.assert_called_once_with("test-col", "sub/doc.md")
        sync_manifest.delete_entry.assert_called_once_with("test-col", "sub/doc.md")

    def test_non_owner_reference_skips_real_delete(self):
        # This source_uri was a deduped reference — it never had real Qdrant content.
        sync_manifest = MagicMock()
        sync_manifest.get_hash_for_source.return_value = "hash123"
        sync_manifest.get_owner.return_value = "other/owner.md"
        client, handler = self._client(sync_manifest)

        resp = client.request("DELETE", "/collections/test-col/documents", params={"source_uri": "sub/doc.md"})

        assert resp.status_code == 200
        handler.container.require_db_provider.return_value.delete_document.assert_not_called()
        sync_manifest.delete_entry.assert_called_once_with("test-col", "sub/doc.md")

    def test_owner_with_remaining_references_hands_off(self):
        # This source_uri IS the owner, but another reference to the same content survives.
        sync_manifest = MagicMock()
        sync_manifest.get_hash_for_source.return_value = "hash123"
        sync_manifest.get_owner.return_value = "sub/doc.md"
        sync_manifest.get_references.return_value = ["sub/doc.md", "other/copy.md"]
        client, handler = self._client(sync_manifest)

        resp = client.request("DELETE", "/collections/test-col/documents", params={"source_uri": "sub/doc.md"})

        assert resp.status_code == 200
        handler.container.require_db_provider.return_value.delete_document.assert_not_called()
        sync_manifest.reassign_owner.assert_called_once_with("test-col", "hash123", "other/copy.md")
        handler.container.require_db_provider.return_value.rename_source.assert_called_once_with("test-col", "sub/doc.md", "other/copy.md")
        sync_manifest.delete_entry.assert_called_once_with("test-col", "sub/doc.md")

    def test_owner_with_no_remaining_references_deletes_for_real(self):
        sync_manifest = MagicMock()
        sync_manifest.get_hash_for_source.return_value = "hash123"
        sync_manifest.get_owner.return_value = "sub/doc.md"
        sync_manifest.get_references.return_value = ["sub/doc.md"]
        client, handler = self._client(sync_manifest)

        resp = client.request("DELETE", "/collections/test-col/documents", params={"source_uri": "sub/doc.md"})

        assert resp.status_code == 200
        handler.container.require_db_provider.return_value.delete_document.assert_called_once_with("test-col", "sub/doc.md")
        sync_manifest.remove_owner.assert_called_once_with("test-col", "hash123")
        sync_manifest.delete_entry.assert_called_once_with("test-col", "sub/doc.md")

    def test_success_is_audited(self):
        # Regression test: ingestion actions used to have no audit trail at
        # all (upload, delete, metadata update, collection delete).
        sync_manifest = MagicMock()
        sync_manifest.get_hash_for_source.return_value = None
        client, handler = self._client(sync_manifest)

        with patch("hestia.api.routers.ingestion.audit") as mock_audit:
            resp = client.request("DELETE", "/collections/test-col/documents", params={"source_uri": "sub/doc.md"})

        assert resp.status_code == 200
        _, kwargs = mock_audit.data_action.call_args
        assert kwargs["action"] == "document_delete"
        assert kwargs["target"] == "test-col"
        assert kwargs["detail"] == {"source_uri": "sub/doc.md"}
        assert kwargs["success"] is True

    def test_failure_is_audited(self):
        sync_manifest = MagicMock()
        sync_manifest.get_hash_for_source.return_value = None
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.require_db_provider.return_value = MagicMock()
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()
        handler.container.services.get.return_value = None
        handler.container.require_db_provider.return_value.delete_document.side_effect = RuntimeError("db down")
        client = TestClient(_app(user=user, handler=handler), raise_server_exceptions=False)

        with patch("hestia.api.routers.ingestion.audit") as mock_audit:
            resp = client.request("DELETE", "/collections/test-col/documents", params={"source_uri": "sub/doc.md"})

        assert resp.status_code == 500
        _, kwargs = mock_audit.data_action.call_args
        assert kwargs["action"] == "document_delete"
        assert kwargs["success"] is False
        assert kwargs["reason"] == "db down"


# ---------------------------------------------------------------------------
# GET /collections/{name}/documents (single document detail)
# ---------------------------------------------------------------------------

class TestGetDocument:

    def test_returns_document_detail(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        db = MagicMock()
        db.get_document.return_value = {
            "source_uri": "doc.pdf", "doc_info": {"title": "T"}, "chunks": [{"id": "c1", "content": "hi"}],
        }
        handler.container.require_db_provider.return_value = db

        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/test-col/documents", params={"source_uri": "doc.pdf"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_info"] == {"title": "T"}
        assert len(data["chunks"]) == 1
        db.get_document.assert_called_once_with("test-col", "doc.pdf")

    def test_returns_404_when_not_found(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        db = MagicMock()
        db.get_document.return_value = None
        handler.container.require_db_provider.return_value = db

        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/test-col/documents", params={"source_uri": "missing.pdf"})

        assert resp.status_code == 404

    def test_non_moderator_forbidden(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/collections/test-col/documents", params={"source_uri": "doc.pdf"})

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /collections/{name}/documents
# ---------------------------------------------------------------------------

class TestUpdateDocumentMetadata:

    def test_updates_metadata_and_derives_classification(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        db = MagicMock()
        db.update_document_metadata.return_value = True
        handler.container.require_db_provider.return_value = db

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/collections/test-col/documents",
            json={"source_uri": "doc.pdf", "metadata": {"title": "New Title", "classification": "confidential"}},
        )

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        db.update_document_metadata.assert_called_once_with(
            "test-col", "doc.pdf", {"title": "New Title", "classification": "confidential"}, 3
        )

    def test_no_classification_field_defaults_to_internal_level(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        db = MagicMock()
        db.update_document_metadata.return_value = True
        handler.container.require_db_provider.return_value = db

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/collections/test-col/documents",
            json={"source_uri": "doc.pdf", "metadata": {"author": "Someone"}},
        )

        assert resp.status_code == 200
        db.update_document_metadata.assert_called_once_with(
            "test-col", "doc.pdf", {"author": "Someone"}, Classification.INTERNAL.level
        )

    def test_returns_404_when_document_not_found(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        db = MagicMock()
        db.update_document_metadata.return_value = False
        handler.container.require_db_provider.return_value = db

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/collections/test-col/documents",
            json={"source_uri": "missing.pdf", "metadata": {}},
        )

        assert resp.status_code == 404

    def test_non_moderator_forbidden(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/collections/test-col/documents",
            json={"source_uri": "doc.pdf", "metadata": {"title": "New Title"}},
        )

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /collections/{name}/sync/diff
# ---------------------------------------------------------------------------

class TestSyncDiff:

    def test_diffs_added_modified_deleted_unmodified(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        sync_manifest = MagicMock()
        sync_manifest.get_manifest.return_value = {
            "unchanged.md": "hash-unchanged",
            "changed.md": "hash-old",
            "removed.md": "hash-removed",
        }
        sync_manifest.get_last_synced_at.return_value = 1700000000
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/collections/test-col/sync/diff",
            json={
                "sync_id": "my-repo",
                "manifest": [
                    {"path": "unchanged.md", "checksum": "hash-unchanged"},
                    {"path": "changed.md", "checksum": "hash-new"},
                    {"path": "new.md", "checksum": "hash-new-file"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] == ["new.md"]
        assert data["modified"] == ["changed.md"]
        assert data["deleted"] == ["removed.md"]
        assert data["unmodified_count"] == 1
        assert data["last_synced_at"] == 1700000000
        sync_manifest.get_last_synced_at.assert_called_once_with("test-col", "my-repo")

    def test_returns_null_last_synced_at_when_never_synced(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        sync_manifest = MagicMock()
        sync_manifest.get_manifest.return_value = {}
        sync_manifest.get_last_synced_at.return_value = None
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/collections/test-col/sync/diff",
            json={"sync_id": "my-repo", "manifest": []},
        )
        assert resp.status_code == 200
        assert resp.json()["last_synced_at"] is None

    def test_returns_previous_classifications_for_modified_only(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        sync_manifest = MagicMock()
        sync_manifest.get_manifest.return_value = {
            "changed.md": "hash-old",
            "unchanged.md": "hash-unchanged",
        }
        sync_manifest.get_last_synced_at.return_value = None
        db = MagicMock()
        db.get_classifications.return_value = {"changed.md": 3}
        handler.container.require_db_provider.return_value = db
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/collections/test-col/sync/diff",
            json={
                "sync_id": "my-repo",
                "manifest": [
                    {"path": "changed.md", "checksum": "hash-new"},
                    {"path": "unchanged.md", "checksum": "hash-unchanged"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["modified"] == ["changed.md"]
        assert data["previous_classifications"] == {"changed.md": "confidential"}
        db.get_classifications.assert_called_once_with("test-col", ["changed.md"])

    def test_previous_classifications_empty_when_level_unresolvable(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        sync_manifest = MagicMock()
        sync_manifest.get_manifest.return_value = {"changed.md": "hash-old"}
        sync_manifest.get_last_synced_at.return_value = None
        db = MagicMock()
        db.get_classifications.return_value = {"changed.md": 99}  # not a real Classification level
        handler.container.require_db_provider.return_value = db
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/collections/test-col/sync/diff",
            json={"sync_id": "my-repo", "manifest": [{"path": "changed.md", "checksum": "hash-new"}]},
        )
        assert resp.status_code == 200
        assert resp.json()["previous_classifications"] == {}

    def test_non_moderator_forbidden(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post(
            "/collections/test-col/sync/diff",
            json={"sync_id": "my-repo", "manifest": []},
        )

        assert resp.status_code == 403


class TestSyncComplete:

    def test_marks_synced(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        sync_manifest = MagicMock()
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post("/collections/test-col/sync/complete", json={"sync_id": "my-repo"})

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        sync_manifest.mark_synced.assert_called_once()
        args = sync_manifest.mark_synced.call_args[0]
        assert args[0] == "test-col"
        assert args[1] == "my-repo"

    def test_non_moderator_forbidden(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post("/collections/test-col/sync/complete", json={"sync_id": "my-repo"})

        assert resp.status_code == 403


class TestDeleteCollection:

    def test_deletes_collection_and_associated_sync_data(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        db = MagicMock()
        db.delete_collection.return_value = True
        handler.container.require_db_provider.return_value = db
        sync_manifest = MagicMock()
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()
        handler.container.services.get.return_value = None

        client = TestClient(_app(user=user, handler=handler))
        resp = client.request("DELETE", "/collections/test-col")

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        db.delete_collection.assert_called_once_with("test-col")
        sync_manifest.delete_collection.assert_called_once_with("test-col")

    def test_returns_404_without_touching_sync_data_when_not_found(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        db = MagicMock()
        db.delete_collection.return_value = False
        handler.container.require_db_provider.return_value = db
        sync_manifest = MagicMock()
        handler.container.services.__getitem__.side_effect = lambda k: sync_manifest if k == "sync_manifest" else MagicMock()

        client = TestClient(_app(user=user, handler=handler))
        resp = client.request("DELETE", "/collections/missing-col")

        assert resp.status_code == 404
        sync_manifest.delete_collection.assert_not_called()

    def test_non_moderator_forbidden(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.request("DELETE", "/collections/test-col")

        assert resp.status_code == 403
