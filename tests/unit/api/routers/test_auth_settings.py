from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.auth_settings import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from tests.unit.conftest import _make_user


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


def _settings_row(**overrides):
    row = {
        "auth_mode": "local",
        "password_min_length": 15,
        "max_failed_attempts": 5,
        "lockout_duration_minutes": 5,
        "token_lifetime_minutes": 360,
        "token_secret_key": "s" * 32,
        "audit_logs": False,
        "ldap_group_mapping": None,
        "oidc_provider_url": "",
        "oidc_client_id": "",
        "oidc_client_secret": "",
        "oidc_scopes": ["openid"],
        "oidc_role_claim": "roles",
        "oidc_role_mapping": None,
        "oidc_org_claim": "organization",
        "oidc_org_mapping": None,
        "ldap_host": "",
        "ldap_port": 636,
        "ldap_search_base": "",
        "ldap_user_attribute": "uid",
        "ldap_mail_attribute": "mail",
        "ldap_use_ssl": True,
        "ldap_validate_cert": True,
        "ldap_bind_dn": None,
        "ldap_bind_password": None,
        "ldap_user_dn_template": None,
        "ldap_allowed_groups": None,
        "updated_at": 1000,
    }
    row.update(overrides)
    return row


def _update_payload(**overrides):
    payload = {
        "auth_mode": "local",
        "password_min_length": 15,
        "max_failed_attempts": 5,
        "lockout_duration_minutes": 5,
        "token_lifetime_minutes": 360,
        "token_secret_key": None,
        "audit_logs": False,
        "ldap_group_mapping": None,
        "oidc_provider_url": "",
        "oidc_client_id": "",
        "oidc_client_secret": None,
        "oidc_scopes": [],
        "oidc_role_claim": "roles",
        "oidc_role_mapping": None,
        "oidc_org_claim": "organization",
        "oidc_org_mapping": None,
        "ldap_host": "",
        "ldap_port": 636,
        "ldap_search_base": "",
        "ldap_user_attribute": "uid",
        "ldap_mail_attribute": "mail",
        "ldap_use_ssl": True,
        "ldap_validate_cert": True,
        "ldap_bind_dn": None,
        "ldap_bind_password": None,
        "ldap_user_dn_template": None,
        "ldap_allowed_groups": None,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# GET /auth/settings
# ---------------------------------------------------------------------------

class TestGetAuthSettings:

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        handler = MagicMock()
        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/auth/settings")
        assert resp.status_code == 403

    def test_returns_503_when_repo_unavailable(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))
        resp = client.get("/auth/settings")
        assert resp.status_code == 503

    def test_masks_secret_fields_and_reports_presence(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row(
            token_secret_key="s" * 32, oidc_client_secret="oidc-secret", ldap_bind_password="ldap-pw",
        )
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))
        resp = client.get("/auth/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "token_secret_key" not in data
        assert "oidc_client_secret" not in data
        assert "ldap_bind_password" not in data
        assert data["has_token_secret_key"] is True
        assert data["has_oidc_client_secret"] is True
        assert data["has_ldap_bind_password"] is True
        assert data["auth_mode"] == "local"

    def test_reports_false_when_secret_fields_empty(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row(
            token_secret_key="", oidc_client_secret="", ldap_bind_password=None,
        )
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))
        resp = client.get("/auth/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_token_secret_key"] is False
        assert data["has_oidc_client_secret"] is False
        assert data["has_ldap_bind_password"] is False


# ---------------------------------------------------------------------------
# PUT /auth/settings
# ---------------------------------------------------------------------------

class TestUpdateAuthSettings:

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        handler = MagicMock()
        client = TestClient(_app(user=user, handler=handler))
        resp = client.put("/auth/settings", json=_update_payload())
        assert resp.status_code == 403

    def test_returns_503_when_repo_unavailable(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))
        resp = client.put("/auth/settings", json=_update_payload())
        assert resp.status_code == 503

    def test_rejects_short_token_secret_key(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row()
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))
        resp = client.put("/auth/settings", json=_update_payload(token_secret_key="short"))
        assert resp.status_code == 400
        repo.update_settings.assert_not_called()

    def test_accepts_token_secret_key_at_minimum_length(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row()
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))
        resp = client.put("/auth/settings", json=_update_payload(token_secret_key="k" * 32))
        assert resp.status_code == 200
        repo.update_settings.assert_called_once()

    def test_happy_path_persists_and_applies_update(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row()
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))

        resp = client.put("/auth/settings", json=_update_payload(auth_mode="ldap", ldap_host="ldap.example.com"))

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        repo.update_settings.assert_called_once()
        kwargs = repo.update_settings.call_args.kwargs
        assert kwargs["auth_mode"] == "ldap"
        assert kwargs["ldap_host"] == "ldap.example.com"
        handler.container.apply_auth_update.assert_called_once()

    def test_bad_ldap_group_mapping_json_shape_is_rejected_by_schema(self):
        # ldap_group_mapping is typed Dict[str, List[str]] -- passing a shape
        # that doesn't fit (e.g. a plain string value instead of a list)
        # must fail FastAPI/pydantic validation before the route body runs.
        handler = MagicMock()
        client = TestClient(_app(handler=handler))
        payload = _update_payload(ldap_group_mapping={"admins": "not-a-list"})
        resp = client.put("/auth/settings", json=payload)
        assert resp.status_code == 422
        handler.container.services.get.assert_not_called()

    def test_blank_secret_fields_omitted_from_changed_but_still_forwarded_as_none(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row(token_secret_key="s" * 32)
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))

        resp = client.put("/auth/settings", json=_update_payload(token_secret_key=None))

        assert resp.status_code == 200
        kwargs = repo.update_settings.call_args.kwargs
        assert kwargs["token_secret_key"] is None

    def test_new_secret_value_is_forwarded(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row()
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))

        resp = client.put("/auth/settings", json=_update_payload(
            oidc_client_secret="new-secret-value", ldap_bind_password="new-ldap-pw",
        ))

        assert resp.status_code == 200
        kwargs = repo.update_settings.call_args.kwargs
        assert kwargs["oidc_client_secret"] == "new-secret-value"
        assert kwargs["ldap_bind_password"] == "new-ldap-pw"


# ---------------------------------------------------------------------------
# POST /auth/settings/test
# ---------------------------------------------------------------------------

class TestTestAuthSettings:

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        handler = MagicMock()
        client = TestClient(_app(user=user, handler=handler))
        resp = client.post("/auth/settings/test", json={"auth_mode": "local"})
        assert resp.status_code == 403

    def test_local_mode_always_ok(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))
        resp = client.post("/auth/settings/test", json={"auth_mode": "local"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_ldap_bind_success(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))

        mock_conn = MagicMock()
        mock_ldap_instance = MagicMock()
        mock_ldap_instance._service_bind.return_value = mock_conn
        with patch("hestia.api.routers.auth_settings.LDAPService", return_value=mock_ldap_instance) as MockLDAP:
            resp = client.post("/auth/settings/test", json={
                "auth_mode": "ldap", "ldap_host": "ldap.example.com", "ldap_bind_dn": "cn=admin",
                "ldap_bind_password": "pw",
            })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_conn.unbind.assert_called_once()
        MockLDAP.assert_called_once()

    def test_ldap_bind_failure_returns_ok_false(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))

        mock_ldap_instance = MagicMock()
        mock_ldap_instance._service_bind.return_value = None
        with patch("hestia.api.routers.auth_settings.LDAPService", return_value=mock_ldap_instance):
            resp = client.post("/auth/settings/test", json={
                "auth_mode": "ldap", "ldap_host": "ldap.example.com", "ldap_bind_dn": "cn=admin",
                "ldap_bind_password": "wrong",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "error" in data

    def test_ldap_unexpected_exception_returns_ok_false(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))

        with patch("hestia.api.routers.auth_settings.LDAPService", side_effect=RuntimeError("boom")):
            resp = client.post("/auth/settings/test", json={
                "auth_mode": "ldap", "ldap_host": "ldap.example.com",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "boom" in data["error"]

    def test_ldap_blank_bind_password_falls_back_to_saved_one(self):
        repo = MagicMock()
        repo.get_settings.return_value = _settings_row(ldap_bind_password="saved-pw")
        handler = MagicMock()
        handler.container.services.get.return_value = repo
        client = TestClient(_app(handler=handler))

        mock_ldap_instance = MagicMock()
        mock_ldap_instance._service_bind.return_value = MagicMock()
        with patch("hestia.api.routers.auth_settings.LDAPService", return_value=mock_ldap_instance) as MockLDAP:
            resp = client.post("/auth/settings/test", json={
                "auth_mode": "ldap", "ldap_host": "ldap.example.com", "ldap_bind_password": None,
            })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        _, call_kwargs = MockLDAP.call_args
        assert call_kwargs["bind_password"] == "saved-pw"

    def test_oidc_missing_provider_url_is_rejected(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))
        resp = client.post("/auth/settings/test", json={"auth_mode": "oidc", "oidc_provider_url": "   "})
        assert resp.status_code == 400

    def test_oidc_reachable_provider_returns_ok(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("hestia.api.routers.auth_settings.requests.get", return_value=mock_resp) as mock_get:
            resp = client.post("/auth/settings/test", json={
                "auth_mode": "oidc", "oidc_provider_url": "https://idp.example.com",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["status"] == 200
        mock_get.assert_called_once_with("https://idp.example.com", timeout=10)

    def test_oidc_unreachable_provider_returns_ok_false(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))

        with patch(
            "hestia.api.routers.auth_settings.requests.get",
            side_effect=requests.ConnectionError("connection refused"),
        ):
            resp = client.post("/auth/settings/test", json={
                "auth_mode": "oidc", "oidc_provider_url": "https://idp.example.com",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "error" in data
