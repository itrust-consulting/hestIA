from __future__ import annotations

import uuid
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from hestia.api.security import (
    assert_admin,
    assert_admin_or_moderator,
    assert_collection_moderator,
    assert_org_member,
    assert_tenant_moderator,
    assert_tenant_role_assigner,
    create_access_token,
    _issue_token,
)
from tests.unit.conftest import _make_user

SECRET = "test-secret-key-at-least-32chars-long!!"
ALG = "HS256"


# ---------------------------------------------------------------------------
# assert_admin
# ---------------------------------------------------------------------------

class TestAssertAdmin:

    def test_passes_for_admin(self, admin_user):
        assert_admin(admin_user)  # no exception

    def test_raises_403_for_non_admin(self, plain_user):
        with pytest.raises(HTTPException) as exc:
            assert_admin(plain_user)
        assert exc.value.status_code == 403

    def test_denial_is_audited(self, plain_user):
        with patch("hestia.api.security.audit") as mock_audit:
            with pytest.raises(HTTPException):
                assert_admin(plain_user)
        mock_audit.access_denied.assert_called_once_with(
            actor_id=str(plain_user.id), action="assert_admin", target=None,
            reason="Admin access required.",
        )


# ---------------------------------------------------------------------------
# assert_admin_or_moderator
# ---------------------------------------------------------------------------

class TestAssertAdminOrModerator:

    def test_passes_for_admin(self, admin_user):
        assert_admin_or_moderator(admin_user)

    def test_passes_for_moderator(self, moderator_user):
        assert_admin_or_moderator(moderator_user)

    def test_raises_403_for_plain_user(self, plain_user):
        with pytest.raises(HTTPException) as exc:
            assert_admin_or_moderator(plain_user)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# assert_org_member
# ---------------------------------------------------------------------------

class TestAssertOrgMember:

    def test_passes_for_admin_regardless_of_org(self, admin_user):
        assert_org_member(admin_user, 999)  # admin_user has no orgs at all

    def test_passes_for_member_of_org(self, plain_user):
        plain_user.orgs = [{"id": 1}, {"id": 2}]
        assert_org_member(plain_user, 1)

    def test_raises_403_for_non_member(self, plain_user):
        plain_user.orgs = [{"id": 1}]
        with pytest.raises(HTTPException) as exc:
            assert_org_member(plain_user, 2)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# assert_tenant_moderator
# ---------------------------------------------------------------------------

class TestAssertTenantModerator:

    def test_passes_for_admin(self, admin_user):
        assert_tenant_moderator(admin_user, 99)  # any org id

    def test_passes_for_moderator_of_org(self, moderator_user):
        assert_tenant_moderator(moderator_user, 1)

    def test_raises_for_wrong_org(self, moderator_user):
        with pytest.raises(HTTPException) as exc:
            assert_tenant_moderator(moderator_user, 999)
        assert exc.value.status_code == 403

    def test_raises_for_plain_user(self, plain_user):
        with pytest.raises(HTTPException):
            assert_tenant_moderator(plain_user, 1)


# ---------------------------------------------------------------------------
# assert_tenant_role_assigner
# ---------------------------------------------------------------------------

class TestAssertTenantRoleAssigner:

    def test_passes_for_admin(self, admin_user):
        assert_tenant_role_assigner(admin_user, 1)

    def test_passes_for_role_assigner_of_org(self):
        user = _make_user(role_assignable_tenants=[1])
        assert_tenant_role_assigner(user, 1)

    def test_raises_for_non_role_assigner(self, plain_user):
        with pytest.raises(HTTPException) as exc:
            assert_tenant_role_assigner(plain_user, 1)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# assert_collection_moderator
# ---------------------------------------------------------------------------

class TestAssertCollectionModerator:

    def _handle(self, users_svc):
        h = MagicMock()
        h.container.services.get.return_value = users_svc
        return h

    def test_passes_for_admin_without_checking_users_service(self, admin_user):
        h = self._handle(users_svc=None)
        assert_collection_moderator(admin_user, "col-1", h)
        h.container.services.get.assert_not_called()

    def test_raises_503_when_users_service_unavailable(self, moderator_user):
        h = self._handle(users_svc=None)
        with pytest.raises(HTTPException) as exc:
            assert_collection_moderator(moderator_user, "col-1", h)
        assert exc.value.status_code == 503

    def test_raises_403_when_collection_has_no_owner(self, moderator_user):
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": None}
        h = self._handle(users_svc=users_svc)
        with pytest.raises(HTTPException) as exc:
            assert_collection_moderator(moderator_user, "col-1", h)
        assert exc.value.status_code == 403

    def test_raises_403_when_user_moderates_a_different_tenant(self, moderator_user):
        # moderator_user moderates tenants [1, 2]; the collection's owner is tenant 99.
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        h = self._handle(users_svc=users_svc)
        with pytest.raises(HTTPException) as exc:
            assert_collection_moderator(moderator_user, "col-1", h)
        assert exc.value.status_code == 403

    def test_passes_when_user_moderates_the_owning_tenant(self, moderator_user):
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 1}}
        h = self._handle(users_svc=users_svc)
        assert_collection_moderator(moderator_user, "col-1", h)  # no exception


# ---------------------------------------------------------------------------
# create_access_token
# ---------------------------------------------------------------------------

class TestCreateAccessToken:

    def test_encodes_user_id_in_sub(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, key=SECRET, algorithm=ALG)
        payload = jwt.decode(token, key=SECRET, algorithms=[ALG])
        assert payload["sub"] == uid.hex

    def test_has_exp_claim(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, key=SECRET, algorithm=ALG)
        payload = jwt.decode(token, key=SECRET, algorithms=[ALG])
        assert "exp" in payload

    def test_token_decodable_with_correct_key(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, key=SECRET, algorithm=ALG)
        payload = jwt.decode(token, key=SECRET, algorithms=[ALG])
        assert payload["sub"] == uid.hex

    def test_expired_token_raises(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, key=SECRET, algorithm=ALG, expiration_time=-1)
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, key=SECRET, algorithms=[ALG])

    def test_allowed_algorithms_still_work(self):
        uid = uuid.uuid4()
        for algorithm in ("HS256", "HS384", "HS512"):
            token = create_access_token(uid, key=SECRET, algorithm=algorithm)
            payload = jwt.decode(token, key=SECRET, algorithms=[algorithm])
            assert payload["sub"] == uid.hex

    def test_disallowed_algorithm_raises_configuration_error(self):
        from hestia.domain.exceptions import ConfigurationError
        uid = uuid.uuid4()
        with pytest.raises(ConfigurationError):
            create_access_token(uid, key=SECRET, algorithm="none")

    def test_has_jti_claim(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, key=SECRET, algorithm=ALG)
        payload = jwt.decode(token, key=SECRET, algorithms=[ALG])
        assert payload.get("jti")

    def test_jti_is_unique_per_token(self):
        uid = uuid.uuid4()
        token_a = create_access_token(uid, key=SECRET, algorithm=ALG)
        token_b = create_access_token(uid, key=SECRET, algorithm=ALG)
        jti_a = jwt.decode(token_a, key=SECRET, algorithms=[ALG])["jti"]
        jti_b = jwt.decode(token_b, key=SECRET, algorithms=[ALG])["jti"]
        assert jti_a != jti_b


# ---------------------------------------------------------------------------
# _issue_token
# ---------------------------------------------------------------------------

class TestIssueToken:

    def test_returns_access_token(self):
        uid = uuid.uuid4()
        result = MagicMock()
        result.user_id = uid
        result.must_change_pw = False

        auth = MagicMock()
        auth.config.token_secret_key = SECRET
        auth.config.token_encoding_alg = ALG
        auth.config.token_lifetime_minutes = 60

        response = _issue_token(result, auth)
        assert "access_token" in response
        assert response["token_type"] == "bearer"

    def test_must_change_pw_included(self):
        uid = uuid.uuid4()
        result = MagicMock()
        result.user_id = uid
        result.must_change_pw = True

        auth = MagicMock()
        auth.config.token_secret_key = SECRET
        auth.config.token_encoding_alg = ALG
        auth.config.token_lifetime_minutes = 60

        response = _issue_token(result, auth)
        assert response["must_change_pw"] is True


from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

class TestGetCurrentUser:

    _NO_AUTH_SVC = object()

    def _container(self, user=None, auth_config=None, auth_svc=_NO_AUTH_SVC):
        if auth_svc is self._NO_AUTH_SVC:
            config = auth_config or MagicMock(token_secret_key=SECRET, token_encoding_alg=ALG)
            auth_svc = MagicMock()
            auth_svc.config = config
            auth_svc.local.repo.is_token_revoked.return_value = False
        user_svc = MagicMock()
        user_svc.load_user_profile.return_value = user
        c = MagicMock()
        c.services.get.side_effect = lambda name: auth_svc if name == "auth" else user_svc
        return c

    def test_returns_user_for_valid_token(self, admin_user):
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        uid = admin_user.id
        token = create_access_token(uid, key=SECRET, algorithm=ALG)
        container = self._container(user=admin_user)

        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {"id": str(user.id)}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_raises_401_on_expired_token(self, admin_user):
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        token = create_access_token(admin_user.id, key=SECRET, algorithm=ALG, expiration_time=-1)
        container = self._container(user=admin_user)
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_expired_token_denial_is_audited(self, admin_user):
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        token = create_access_token(admin_user.id, key=SECRET, algorithm=ALG, expiration_time=-1)
        container = self._container(user=admin_user)
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        with patch("hestia.api.security.audit") as mock_audit:
            resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        mock_audit.access_denied.assert_called_once_with(
            actor_id="unknown", action="get_current_user", reason="token_expired",
        )

    def test_raises_500_on_disallowed_signing_algorithm(self, admin_user):
        # Regression test: a misconfigured (or, if ever admin-exposed,
        # attacker-influenced) token_encoding_alg must never reach
        # jwt.decode's algorithms= list unvalidated -- e.g. "none" would
        # disable signature verification entirely.
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        bad_config = MagicMock(token_secret_key=SECRET, token_encoding_alg="none")
        container = self._container(user=admin_user, auth_config=bad_config)
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": "Bearer whatever"})
        assert resp.status_code == 500

    def test_raises_401_on_malformed_token(self, admin_user):
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        container = self._container(user=admin_user)
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
        assert resp.status_code == 401

    def test_raises_401_when_token_has_no_sub_claim(self, admin_user):
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        # A validly-signed token that simply lacks a "sub" claim.
        token = jwt.encode({"exp": 9999999999}, SECRET, algorithm=ALG)
        container = self._container(user=admin_user)
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": "Bearer " + token})
        assert resp.status_code == 401

    def test_raises_401_for_revoked_token(self, admin_user):
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        token = create_access_token(admin_user.id, key=SECRET, algorithm=ALG)
        container = self._container(user=admin_user)
        container.services.get.side_effect = None
        auth_svc = MagicMock(config=MagicMock(token_secret_key=SECRET, token_encoding_alg=ALG))
        auth_svc.local.repo.is_token_revoked.return_value = True
        user_svc = MagicMock()
        user_svc.load_user_profile.return_value = admin_user
        container.services.get.side_effect = lambda name: auth_svc if name == "auth" else user_svc
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        auth_svc.local.repo.is_token_revoked.assert_called_once()

    def test_raises_401_when_user_not_found(self):
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        uid = uuid.uuid4()
        token = create_access_token(uid, key=SECRET, algorithm=ALG)
        # No user found for this id in the user service.
        container = self._container(user=None)
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_raises_when_auth_service_itself_is_missing(self):
        # If "auth" isn't registered at all (not just missing a config),
        # there's no token secret/algorithm to validate against -- this must
        # not silently fall through and accept an unverifiable token.
        from hestia.api.security import get_current_user
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hestia.api.dependencies import get_container

        container = self._container(auth_svc=None)
        app = FastAPI()
        app.dependency_overrides[get_container] = lambda: container

        @app.get("/me")
        def me(user=__import__("fastapi").Depends(get_current_user)):
            return {}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": "Bearer whatever"})
        assert resp.status_code == 500
