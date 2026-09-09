"""TST-015 - Unauthenticated access denied (SRS-004/SRS-005).

This suite is black-box against the REST API, which has no server-rendered
"pages" to redirect from - "redirected to the login page" (the TST's
UI-level wording) is translated here to the API-level equivalent: any
protected endpoint must reject an unauthenticated request with 401/403,
never silently succeed.

Expected outcome:
1. No protected endpoint is accessible and every one denies access without
   a valid token.
"""
import pytest

from conftest import ApiClient

PROTECTED_ENDPOINTS = [
    ("get", "/account"),
    ("get", "/admin/organizations"),
    ("get", "/admin/logs"),
    ("post", "/api/search"),
]


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_protected_endpoint_denied_without_token(method, path):
    client = ApiClient()
    resp = getattr(client, method)(path, json={} if method == "post" else None)
    assert resp.status_code in (401, 403), (
        f"{method.upper()} {path} should deny an unauthenticated request, "
        f"got {resp.status_code}: {resp.text}"
    )
