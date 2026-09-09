"""TST-014 - User access expiration (SRS-005: time-bounded access grants).

Expected outcome:
1. Before expires_at, the user account functions normally.
2. After expires_at, login (or continued access) is denied.
3. Before starts_at, a tenant-role grant is not yet active and does not
   grant access.
4. After starts_at, the role grant becomes active.
"""
import time

import pytest

from conftest import login


def _epoch_in(delta_seconds: int) -> int:
    """CreateUserRequest.expires_at is an int epoch-seconds timestamp
    (hestia/api/schemas/requests.py:78), not an ISO string."""
    return int(time.time()) + delta_seconds


def test_user_functions_normally_before_expiry(make_user):
    user = make_user(expires_at=_epoch_in(3600))
    resp = user.login()
    assert resp.status_code == 200, resp.text

    account = user.client.get("/account")
    assert account.status_code == 200, account.text


def test_access_denied_after_expiry(make_user):
    user = make_user(expires_at=_epoch_in(3))
    resp = user.login()
    assert resp.status_code == 200, resp.text

    time.sleep(5)

    denied_login = login(user.client, user.username, user.password)
    account_check = user.client.get("/account")

    assert denied_login.status_code in (400, 401, 403) or account_check.status_code in (401, 403), (
        f"expected access to be denied after expires_at: "
        f"re-login={denied_login.status_code}, existing-token-check={account_check.status_code}"
    )


@pytest.mark.skip(
    reason="No API path sets a future starts_at on a role grant: "
    "UserService.create_user (hestia/domain/auth/users.py:239) always calls "
    "add_role_to_user with starts_ts=ts (creation time, hardcoded); "
    "update_user's role_ids path (users.py:278) also hardcodes starts_ts=now. "
    "user_roles.starts_at exists at the DB layer but nothing above it accepts "
    "a caller-supplied value. This is a real gap between SRS-005's "
    "time-bounded-access criterion and the current API surface -- flag for "
    "follow-up rather than faking this assertion."
)
def test_role_grant_starts_at_gates_access():
    pass
