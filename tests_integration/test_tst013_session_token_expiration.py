"""TST-013 - Session expiration (SRS-004).

Requires the live instance to have a short AUTH_TOKEN_LIFETIME (e.g. 60-90s)
for the expiry portion to be practical to wait out - see README. Logout
(token revocation via jti) is testable regardless of the configured lifetime.

Expected outcome:
1. Once the token has expired, the protected feature is inaccessible.
2. A token invalidated by logout is rejected immediately, even though it
   has not yet naturally expired.
"""
import os
import time

import pytest

from conftest import ApiClient, login, ADMIN_USERNAME, ADMIN_PASSWORD

TOKEN_LIFETIME_SECONDS = int(os.environ.get("HESTIA_AUTH_TOKEN_LIFETIME_SECONDS", "0"))


def test_logout_revokes_token_immediately(admin_client, make_user):
    user = make_user()
    resp = user.login()
    assert resp.status_code == 200, resp.text

    still_valid = user.client.get("/account")
    assert still_valid.status_code == 200, still_valid.text

    logout_resp = user.client.post("/logout")
    assert logout_resp.status_code in (200, 204), logout_resp.text

    after_logout = user.client.get("/account")
    assert after_logout.status_code in (401, 403), (
        f"expected the revoked token to be rejected immediately, got "
        f"{after_logout.status_code}: {after_logout.text}"
    )


@pytest.mark.skipif(
    TOKEN_LIFETIME_SECONDS <= 0 or TOKEN_LIFETIME_SECONDS > 180,
    reason="set HESTIA_AUTH_TOKEN_LIFETIME_SECONDS to a short value (matching the "
    "live instance's AUTH_TOKEN_LIFETIME, converted to seconds) to run the actual "
    "expiry-wait portion of this test",
)
def test_token_rejected_after_natural_expiry(make_user):
    user = make_user()
    resp = user.login()
    assert resp.status_code == 200, resp.text

    time.sleep(TOKEN_LIFETIME_SECONDS + 5)

    expired = user.client.get("/account")
    assert expired.status_code in (401, 403), (
        f"expected an expired token to be rejected, got "
        f"{expired.status_code}: {expired.text}"
    )
