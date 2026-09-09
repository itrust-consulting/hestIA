"""TST-008 - LDAP authentication - Configuration (SRS-004).

Requires a live instance running with AUTH_MODE=ldap, LDAP_GROUP_MAPPING
configured with at least two groups mapped to different hestIA roles, and
one test user in each group. Skipped unless the corresponding env vars are
set - this session cannot provision an LDAP test server itself.

Per plan: asserts against the live instance's current LDAP config; flipping
LDAP_* env vars and restarting to test a *different* mapping is a
manual/CI step, not scripted here.

Expected outcome:
2. A user's group membership correctly determines their assigned hestIA role.
"""
import os

import pytest

from conftest import ApiClient, login

GROUP1_USERNAME = os.environ.get("HESTIA_LDAP_TEST_USERNAME")
GROUP1_PASSWORD = os.environ.get("HESTIA_LDAP_TEST_PASSWORD")
GROUP1_EXPECTED_ROLE = os.environ.get("HESTIA_LDAP_TEST_ROLE")

GROUP2_USERNAME = os.environ.get("HESTIA_LDAP_TEST_GROUP2_USERNAME")
GROUP2_PASSWORD = os.environ.get("HESTIA_LDAP_TEST_GROUP2_PASSWORD")
GROUP2_EXPECTED_ROLE = os.environ.get("HESTIA_LDAP_TEST_GROUP2_ROLE")

pytestmark = pytest.mark.skipif(
    not (GROUP1_USERNAME and GROUP1_PASSWORD and GROUP2_USERNAME and GROUP2_PASSWORD),
    reason="HESTIA_LDAP_TEST_(GROUP2_)USERNAME/PASSWORD not set; requires a live "
    "instance running AUTH_MODE=ldap with two role-mapped test groups",
)


def _whoami_role(client: ApiClient) -> str:
    resp = client.get("/account")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    roles = body.get("roles") or body.get("role_ids") or [body.get("role")]
    return roles[0] if roles else None


def test_group1_user_gets_mapped_role():
    client = ApiClient()
    resp = login(client, GROUP1_USERNAME, GROUP1_PASSWORD)
    assert resp.status_code == 200, resp.text
    client.set_token(resp.json()["access_token"])
    if GROUP1_EXPECTED_ROLE:
        assert _whoami_role(client) == GROUP1_EXPECTED_ROLE


def test_group2_user_gets_a_different_mapped_role():
    client1, client2 = ApiClient(), ApiClient()

    r1 = login(client1, GROUP1_USERNAME, GROUP1_PASSWORD)
    assert r1.status_code == 200, r1.text
    client1.set_token(r1.json()["access_token"])

    r2 = login(client2, GROUP2_USERNAME, GROUP2_PASSWORD)
    assert r2.status_code == 200, r2.text
    client2.set_token(r2.json()["access_token"])

    role1, role2 = _whoami_role(client1), _whoami_role(client2)
    assert role1 != role2, (
        f"expected group1 ({role1!r}) and group2 ({role2!r}) users to resolve "
        "to different hestIA roles per LDAP_GROUP_MAPPING"
    )
    if GROUP2_EXPECTED_ROLE:
        assert role2 == GROUP2_EXPECTED_ROLE
