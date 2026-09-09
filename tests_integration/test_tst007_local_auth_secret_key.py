"""TST-007 - Local authentication - Configuration (SRS-004).

Per plan: asserts against whatever config the live instance already has
when the test runs; flipping AUTH_SECRET_KEY / AUTH_MODE and restarting the
service to exercise the "refuses to start" branch is a manual/CI step, not
scripted here.

Expected outcome:
1. Login uses the local credential store directly, with no external redirect.
3. With a valid AUTH_SECRET_KEY, the service starts normally and local login
   succeeds.
"""
from conftest import ApiClient, login, ADMIN_USERNAME, ADMIN_PASSWORD

# Both checks below are properties of a single login response, deliberately
# combined into one test function -> one /login call for username "admin".
# The live instance's login endpoint is rate-limited per-username across
# ALL requests (not just failures, see hestia/api/limiter.py), and this
# module previously made two independent admin logins on top of the ones in
# test_tst004 and the session-scoped admin_client fixture - enough on its
# own to exhaust a "5 per 5 minutes" budget and 429 every other test in the
# suite. Keep this file to exactly one admin login.


def test_local_login_succeeds_with_no_external_redirect():
    """If the instance is reachable and login succeeds, AUTH_SECRET_KEY is
    valid (a missing/too-short key prevents the service from issuing tokens
    at all, per hestia/api/security.py). Local mode also returns a token
    directly, with no OIDC-style redirect (no 3xx, no Location header)."""
    client = ApiClient()
    resp = login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert resp.status_code == 200, (
        f"login failed ({resp.status_code}): {resp.text}\n"
        "If this is due to a missing/short AUTH_SECRET_KEY, that is exactly "
        "the failure mode TST-007 documents (see the SRS/TST manual-restart note)."
    )
    token = resp.json()["access_token"]
    assert token and isinstance(token, str)
    assert "Location" not in resp.headers
    assert not (300 <= resp.status_code < 400)
