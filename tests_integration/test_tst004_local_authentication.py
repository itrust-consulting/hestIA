"""TST-004 - Local authentication (SRS-004).

Expected outcome:
1. The protected feature is inaccessible before authentication.
2. Valid credentials grant access to the system.
3. Invalid credentials are rejected with a clear error message, and no
   access is granted.
"""
from conftest import ApiClient, login, ADMIN_USERNAME, ADMIN_PASSWORD


def test_protected_endpoint_denied_without_auth():
    client = ApiClient()
    resp = client.get("/admin/organizations")
    assert resp.status_code in (401, 403), resp.text


def test_valid_credentials_grant_access():
    client = ApiClient()
    resp = login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("access_token"), body
    assert body.get("token_type", "").lower() == "bearer"

    client.set_token(body["access_token"])
    protected = client.get("/admin/organizations")
    assert protected.status_code == 200, protected.text


def test_invalid_credentials_rejected_with_clear_error():
    client = ApiClient()
    resp = login(client, ADMIN_USERNAME, "definitely-not-the-password")
    assert resp.status_code in (400, 401), resp.text
    assert resp.json().get("detail"), "error response should carry a description"

    client.set_token(None)
    protected = client.get("/admin/organizations")
    assert protected.status_code in (401, 403)
