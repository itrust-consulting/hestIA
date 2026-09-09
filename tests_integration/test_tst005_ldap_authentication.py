"""TST-005 - LDAP authentication (SRS-004).

Requires a live instance configured with AUTH_MODE=ldap against a reachable
test directory, plus a known-good test user in it. Skipped unless
HESTIA_LDAP_TEST_USERNAME/HESTIA_LDAP_TEST_PASSWORD are set — this session
has no way to provision an LDAP test server itself.

Expected outcome:
1. A valid LDAP user is authenticated and granted access to the system.
2. An incorrect password for a valid LDAP user is rejected with a clear error.
3. A non-existent LDAP username is rejected with a clear error.
"""
import os

import pytest

from conftest import ApiClient, login

LDAP_USERNAME = os.environ.get("HESTIA_LDAP_TEST_USERNAME")
LDAP_PASSWORD = os.environ.get("HESTIA_LDAP_TEST_PASSWORD")

pytestmark = pytest.mark.skipif(
    not (LDAP_USERNAME and LDAP_PASSWORD),
    reason="HESTIA_LDAP_TEST_USERNAME/HESTIA_LDAP_TEST_PASSWORD not set; "
    "requires a live instance running with AUTH_MODE=ldap against a reachable directory",
)


def test_valid_ldap_user_authenticates():
    client = ApiClient()
    resp = login(client, LDAP_USERNAME, LDAP_PASSWORD)
    assert resp.status_code == 200, resp.text
    assert resp.json().get("access_token")


def test_incorrect_password_rejected():
    client = ApiClient()
    resp = login(client, LDAP_USERNAME, LDAP_PASSWORD + "-wrong")
    assert resp.status_code in (400, 401), resp.text
    assert resp.json().get("detail")


def test_nonexistent_ldap_username_rejected():
    client = ApiClient()
    resp = login(client, f"nonexistent-{os.urandom(4).hex()}", "irrelevant")
    assert resp.status_code in (400, 401), resp.text
    assert resp.json().get("detail")
