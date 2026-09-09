"""TST-017 - Admin-accessible pages blocked for non-admin roles (SRS-005).

Black-box translation: "admin accessible pages" -> endpoints guarded by
assert_admin (e.g. POST /admin/users/create). A plain user or a tenant
moderator account must receive 403 - moderator is a per-tenant membership
attribute (not a system role, see conftest._role_id_map), so exercising it
requires an org + membership + role-set, not just make_user(roles=...).

Expected outcome:
1. The user is shown a 403.
"""


def _assert_denied_admin_only_endpoint(client):
    denied = client.post(
        "/admin/users/create",
        json={
            "username": "should-not-be-created",
            "email": "nope@example.invalid",
            "password": "Irrelevant123!",
            "first_name": "x",
            "last_name": "y",
        },
    )
    assert denied.status_code == 403, (
        f"expected the caller to be denied an admin-only endpoint, got "
        f"{denied.status_code}: {denied.text}"
    )


def test_plain_user_denied_admin_only_endpoint(make_user):
    user = make_user(roles=["user"])
    resp = user.login()
    assert resp.status_code == 200, resp.text
    _assert_denied_admin_only_endpoint(user.client)


def test_tenant_moderator_denied_admin_only_endpoint(admin_client, make_user, make_org):
    user = make_user(roles=["user"])
    org = make_org()
    org_id = org.get("id") or org.get("org_id") or org.get("organization_id")

    add_member = admin_client.post(f"/admin/organizations/{org_id}/members/{user.user_id}")
    assert add_member.status_code == 200, add_member.text

    set_role = admin_client.patch(
        f"/admin/organizations/{org_id}/members/{user.user_id}/role", json={"role": "moderator"}
    )
    assert set_role.status_code == 200, set_role.text

    resp = user.login()
    assert resp.status_code == 200, resp.text
    _assert_denied_admin_only_endpoint(user.client)
