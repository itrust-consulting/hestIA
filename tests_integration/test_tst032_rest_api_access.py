"""TST-032 - REST API access (SRS-007).

Expected outcome:
1. A valid token is issued and accepted by subsequent API calls.
2. Core features are fully usable via the API without the web interface.
3. API responses follow a consistent structure across endpoints.
4. Error responses clearly describe what went wrong.
5. API documentation is available and describes all supported operations.
"""
import os

from conftest import ApiClient, login, search_text, ADMIN_USERNAME, ADMIN_PASSWORD, ASSETS_DIR


def test_token_issued_and_accepted():
    client = ApiClient()
    resp = login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    client.set_token(token)
    core_call = client.get("/admin/organizations")
    assert core_call.status_code == 200, core_call.text


def test_core_feature_usable_end_to_end_via_api(admin_client, make_collection):
    """Ingest and search a document purely through the API, no UI."""
    collection = make_collection()
    fixture = os.path.join(ASSETS_DIR, "formats", "operational-notes.txt")

    with open(fixture, "rb") as fh:
        upload = admin_client.post(
            "/api/upload",
            files={"file": ("operational-notes.txt", fh)},
            data={"collection": collection},
        )
    assert upload.status_code == 200, upload.text
    assert upload.json().get("ok") is True

    search = search_text(admin_client, collection, "maintenance window", mode="keyword")
    assert search.status_code == 200, search.text


def test_error_response_describes_the_problem(admin_client):
    resp = admin_client.post("/api/search", json={"mode": "keyword", "collection": "x"})  # missing query
    assert resp.status_code in (400, 422), resp.text
    body = resp.json()
    assert body.get("detail"), f"error body should describe what went wrong: {body}"


def test_openapi_documentation_available():
    client = ApiClient()
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, resp.text
    schema = resp.json()
    assert "paths" in schema and len(schema["paths"]) > 0
    assert "/login" in schema["paths"]
