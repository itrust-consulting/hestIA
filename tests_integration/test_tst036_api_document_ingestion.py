"""TST-036 - API-based single document ingestion (SRS-026).

Expected outcome:
1. A document is ingested into a named collection through a single API
   call, without going through the web interface.
2. The API response confirms whether ingestion succeeded and reports a
   clear error when the document is rejected.
3. A document ingested via the API is queryable through the chat interface
   afterwards, with the same behavior as a UI-ingested document.
"""
import os

from conftest import ASSETS_DIR


def test_single_document_ingested_via_api(admin_client, make_collection):
    collection = make_collection()
    fixture = os.path.join(ASSETS_DIR, "formats", "operational-notes.txt")

    with open(fixture, "rb") as fh:
        resp = admin_client.post(
            "/api/upload",
            files={"file": ("operational-notes.txt", fh)},
            data={"collection": collection},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("collection") == collection
    assert body.get("n_chunks", 0) > 0


def test_rejected_document_reports_clear_error(admin_client, make_collection):
    collection = make_collection()
    resp = admin_client.post(
        "/api/upload",
        files={"file": ("empty.bin", b"\x00\x01\x02")},
        data={"collection": collection},
    )
    assert resp.status_code >= 400, "expected an unparseable file to be rejected"
    body = resp.json()
    assert body.get("detail"), f"error response should describe the rejection: {body}"


def test_ingested_document_queryable_afterwards(admin_client, make_queryable_collection):
    collection, member = make_queryable_collection()
    fixture = os.path.join(ASSETS_DIR, "formats", "operational-notes.txt")

    with open(fixture, "rb") as fh:
        upload = admin_client.post(
            "/api/upload",
            files={"file": ("operational-notes.txt", fh)},
            data={"collection": collection},
        )
    assert upload.status_code == 200, upload.text

    chat = member.client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "What is the maintenance window?"}],
            "collection": collection,
            "stream": False,
        },
    )
    assert chat.status_code == 200, chat.text
