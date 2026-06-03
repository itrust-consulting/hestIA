from __future__ import annotations

import uuid

import jwt
import pytest
from fastapi import HTTPException

from hestia.api.security import (
    assert_admin,
    assert_admin_or_moderator,
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

    def test_raises_for_non_role_assigner(self, plain_user):
        with pytest.raises(HTTPException) as exc:
            assert_tenant_role_assigner(plain_user, 1)
        assert exc.value.status_code == 403


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

    def _container(self, user=None, auth_config=None):
        config = auth_config or MagicMock(token_secret_key=SECRET, token_encoding_alg=ALG)
        auth_svc = MagicMock()
        auth_svc.config = config
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
