"""TST-012 - Rate limiting (SRS-020).

Uses a disposable user (not the shared admin) so the per-username lockout
(hestia/api/limiter.py: keyed on the submitted `username`, not IP) cannot
affect any other test. Requires the live instance's AUTH_MAX_ATTEMPTS /
AUTH_LOCKOUT_DURATION to be reasonably small for the "wait it out" portion
to be practical in a test run - see README.

Expected outcome:
1. The 6th attempt (beyond the configured threshold, default 5) returns
   HTTP 429, even with the correct password.
2. After the lockout window elapses, a correct-password login succeeds again.
"""
import os
import time

import pytest

from conftest import ApiClient, login

MAX_ATTEMPTS = int(os.environ.get("HESTIA_AUTH_MAX_ATTEMPTS", "5"))
LOCKOUT_SECONDS = int(os.environ.get("HESTIA_AUTH_LOCKOUT_SECONDS", "60"))


def test_exceeding_threshold_returns_429(make_user):
    user = make_user()
    client = ApiClient()

    for _ in range(MAX_ATTEMPTS):
        resp = login(client, user.username, "definitely-wrong-password")
        assert resp.status_code in (400, 401), resp.text

    over_limit = login(client, user.username, user.password)  # correct pw, still over budget
    assert over_limit.status_code == 429, (
        f"expected 429 after {MAX_ATTEMPTS} failed attempts, got "
        f"{over_limit.status_code}: {over_limit.text}"
    )


@pytest.mark.skipif(
    LOCKOUT_SECONDS > 180,
    reason="HESTIA_AUTH_LOCKOUT_SECONDS is too long to wait out in a test run; "
    "point this at an instance configured with a short AUTH_LOCKOUT_DURATION",
)
def test_login_succeeds_again_after_lockout_window(make_user):
    user = make_user()
    client = ApiClient()

    for _ in range(MAX_ATTEMPTS):
        login(client, user.username, "definitely-wrong-password")

    locked = login(client, user.username, user.password)
    assert locked.status_code == 429, locked.text

    time.sleep(LOCKOUT_SECONDS + 2)

    recovered = login(client, user.username, user.password)
    assert recovered.status_code == 200, (
        f"expected login to succeed after the lockout window elapsed, got "
        f"{recovered.status_code}: {recovered.text}"
    )
