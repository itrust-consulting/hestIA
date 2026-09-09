"""TST-016 - Moderator-accessible pages blocked for a plain user (SRS-005).

Black-box translation: "moderator accessible pages" -> endpoints guarded by
assert_admin_or_moderator / assert_tenant_moderator. A plain "user"-role
account must receive 403.

Expected outcome:
1. The user is shown a 403.
"""
from conftest import ApiClient


def test_plain_user_denied_moderator_endpoint(make_user):
    user = make_user(roles=["user"])
    resp = user.login()
    assert resp.status_code == 200, resp.text

    denied = user.client.post("/admin/collections/create", json={"name": "should-not-be-created"})
    assert denied.status_code == 403, (
        f"expected a plain user to be denied a moderator-only endpoint, got "
        f"{denied.status_code}: {denied.text}"
    )
