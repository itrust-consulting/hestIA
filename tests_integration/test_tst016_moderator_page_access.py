"""TST-016 - Moderator-accessible pages blocked for a plain user (SRS-005).

Black-box translation: "moderator accessible pages" -> endpoints guarded by
assert_admin_or_moderator, assert_tenant_moderator, assert_tenant_role_assigner,
assert_org_member, or assert_collection_moderator. A plain "user"-role account
must receive 403. Each guard gets one representative endpoint here rather than
one test per guarded route -- the guard function itself doesn't vary route to
route, and the exhaustive per-route case is already covered at the unit level
(tests/unit/api/routers/*.py's test_non_admin_forbidden / test_non_moderator_forbidden
tests).

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


def test_plain_user_denied_tenant_moderator_endpoint(make_user, make_org):
    org = make_org()
    org_id = org["id"]
    user = make_user(roles=["user"])
    resp = user.login()
    assert resp.status_code == 200, resp.text

    denied = user.client.get(f"/admin/organizations/{org_id}/members")
    assert denied.status_code == 403, (
        f"expected a plain user to be denied a tenant-moderator-only endpoint, got "
        f"{denied.status_code}: {denied.text}"
    )


def test_non_member_denied_org_summary(make_user, make_org):
    # assert_org_member gates GET /organizations/{id}/summary.
    org = make_org()
    org_id = org["id"]
    user = make_user(roles=["user"])
    resp = user.login()
    assert resp.status_code == 200, resp.text

    denied = user.client.get(f"/organizations/{org_id}/summary")
    assert denied.status_code == 403, (
        f"expected a non-member to be denied that tenant's summary, got "
        f"{denied.status_code}: {denied.text}"
    )


def test_non_role_assigner_denied_setting_member_role(admin_client, make_user, make_org):
    # assert_tenant_role_assigner gates PATCH .../members/{user_id}/role --
    # a distinct permission from assert_tenant_moderator: being the tenant's
    # moderator doesn't by itself grant role-assignment rights.
    org = make_org()
    org_id = org["id"]

    target = make_user(roles=["user"])
    add_member = admin_client.post(f"/admin/organizations/{org_id}/members/{target.user_id}")
    assert add_member.status_code == 200, add_member.text

    actor = make_user(roles=["user"])
    resp = actor.login()
    assert resp.status_code == 200, resp.text

    denied = actor.client.patch(
        f"/admin/organizations/{org_id}/members/{target.user_id}/role",
        json={"role": "moderator"},
    )
    assert denied.status_code == 403, (
        f"expected a non-role-assigner to be denied setting a tenant member's role, got "
        f"{denied.status_code}: {denied.text}"
    )


def test_non_moderator_denied_collection_delete(make_user, make_org, make_collection):
    # assert_collection_moderator gates DELETE /api/collections/{name} (plus
    # upload, document CRUD, and sync on ingestion.py) -- derives access from
    # the collection's *owning tenant*, not simple admin/moderator status.
    org = make_org()
    collection = make_collection(owner_org_id=org["id"])
    user = make_user(roles=["user"])
    resp = user.login()
    assert resp.status_code == 200, resp.text

    denied = user.client.delete(f"/api/collections/{collection}")
    assert denied.status_code == 403, (
        f"expected a non-moderator to be denied deleting a collection, got "
        f"{denied.status_code}: {denied.text}"
    )
