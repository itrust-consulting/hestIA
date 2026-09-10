from __future__ import annotations

import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest
import requests as req

from hestia.config.settings import OIDCSettings
from hestia.domain.auth.oidc import OIDCService
from hestia.domain.auth.service import AuthenticationService


PROVIDER_URL = "https://idp.example.com/realms/test"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def oidc_settings():
    return OIDCSettings(
        provider_url=PROVIDER_URL,
        client_id="hestia-client",
        client_secret="s3cr3t",
        scopes=["openid", "profile", "email"],
        role_claim="roles",
        role_mapping={"hestia-admin": ["admin"], "hestia-user": ["user"]},
    )


@pytest.fixture
def oidc_service(oidc_settings):
    return OIDCService(oidc_settings)


@pytest.fixture
def mock_user_service():
    svc = MagicMock()
    svc.repo = MagicMock()
    return svc


@pytest.fixture
def auth_service(mock_user_service, oidc_service):
    return AuthenticationService(local=mock_user_service, oidc=oidc_service)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token_response(access_token="access-tok"):
    resp = MagicMock()
    resp.json.return_value = {"access_token": access_token, "token_type": "Bearer"}
    return resp


def _userinfo_response(**overrides):
    data = {
        "sub": "u-1",
        "email": "alice@example.com",
        "preferred_username": "alice",
        "given_name": "Alice",
        "family_name": "Dupont",
        "roles": ["hestia-user"],
    }
    data.update(overrides)
    resp = MagicMock()
    resp.json.return_value = data
    return resp


# ---------------------------------------------------------------------------
# OIDCService.get_authorization_url
# ---------------------------------------------------------------------------

class TestGetAuthorizationUrl:

    def test_points_to_provider_auth_endpoint(self, oidc_service):
        url = oidc_service.get_authorization_url("https://app/callback", "st")
        assert url.startswith(f"{PROVIDER_URL}/protocol/openid-connect/auth")

    def test_contains_client_id(self, oidc_service):
        url = oidc_service.get_authorization_url("https://app/callback", "st")
        assert "client_id=hestia-client" in url

    def test_contains_state(self, oidc_service):
        url = oidc_service.get_authorization_url("https://app/callback", "my-state")
        assert "state=my-state" in url

    def test_response_type_is_code(self, oidc_service):
        url = oidc_service.get_authorization_url("https://app/callback", "st")
        assert "response_type=code" in url

    def test_scopes_present(self, oidc_service):
        url = oidc_service.get_authorization_url("https://app/callback", "st")
        assert "openid" in url
        assert "profile" in url
        assert "email" in url

    def test_no_pkce_params_when_challenge_omitted(self, oidc_service):
        url = oidc_service.get_authorization_url("https://app/callback", "st")
        assert "code_challenge" not in url

    def test_pkce_params_included_when_challenge_given(self, oidc_service):
        url = oidc_service.get_authorization_url("https://app/callback", "st", code_challenge="abc123")
        assert "code_challenge=abc123" in url
        assert "code_challenge_method=S256" in url


# ---------------------------------------------------------------------------
# OIDCService.exchange_code
# ---------------------------------------------------------------------------

class TestExchangeCode:

    def test_returns_token_data(self, oidc_service):
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()):
            result = asyncio.run(oidc_service.exchange_code("auth-code", "https://app/callback"))
        assert result["access_token"] == "access-tok"

    def test_posts_correct_grant_type(self, oidc_service):
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()) as mock_post:
            asyncio.run(oidc_service.exchange_code("auth-code", "https://app/callback"))
        payload = mock_post.call_args.kwargs["data"]
        assert payload["grant_type"] == "authorization_code"
        assert payload["client_id"] == "hestia-client"
        assert payload["client_secret"] == "s3cr3t"
        assert payload["code"] == "auth-code"

    def test_raises_on_http_error(self, oidc_service):
        bad_resp = MagicMock()
        bad_resp.raise_for_status.side_effect = req.HTTPError("401")
        with patch("hestia.domain.auth.oidc.requests.post", return_value=bad_resp):
            with pytest.raises(req.HTTPError):
                asyncio.run(oidc_service.exchange_code("bad-code", "https://app/callback"))

    def test_no_code_verifier_key_when_omitted(self, oidc_service):
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()) as mock_post:
            asyncio.run(oidc_service.exchange_code("auth-code", "https://app/callback"))
        assert "code_verifier" not in mock_post.call_args.kwargs["data"]

    def test_includes_code_verifier_when_given(self, oidc_service):
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()) as mock_post:
            asyncio.run(oidc_service.exchange_code("auth-code", "https://app/callback", code_verifier="verifier-123"))
        assert mock_post.call_args.kwargs["data"]["code_verifier"] == "verifier-123"


# ---------------------------------------------------------------------------
# OIDCService.get_user_info
# ---------------------------------------------------------------------------

class TestGetUserInfo:

    def test_returns_user_info(self, oidc_service):
        with patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response()):
            result = asyncio.run(oidc_service.get_user_info("tok-123"))
        assert result["email"] == "alice@example.com"

    def test_sends_bearer_header(self, oidc_service):
        with patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response()) as mock_get:
            asyncio.run(oidc_service.get_user_info("my-token"))
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-token"

    def test_raises_on_http_error(self, oidc_service):
        bad_resp = MagicMock()
        bad_resp.raise_for_status.side_effect = req.HTTPError("401")
        with patch("hestia.domain.auth.oidc.requests.get", return_value=bad_resp):
            with pytest.raises(req.HTTPError):
                asyncio.run(oidc_service.get_user_info("expired-token"))


# ---------------------------------------------------------------------------
# OIDCService.extract_roles
# ---------------------------------------------------------------------------

class TestExtractRoles:

    def test_list_claim(self, oidc_service):
        assert oidc_service.extract_roles({"roles": ["hestia-admin", "hestia-user"]}) == [
            "hestia-admin", "hestia-user"
        ]

    def test_string_claim(self, oidc_service):
        assert oidc_service.extract_roles({"roles": "hestia-user"}) == ["hestia-user"]

    def test_missing_claim_returns_empty(self, oidc_service):
        assert oidc_service.extract_roles({}) == []

    def test_none_claim_returns_empty(self, oidc_service):
        assert oidc_service.extract_roles({"roles": None}) == []

    def test_custom_claim_key(self, oidc_settings):
        oidc_settings.role_claim = "groups"
        svc = OIDCService(oidc_settings)
        assert svc.extract_roles({"groups": ["devs"]}) == ["devs"]


# ---------------------------------------------------------------------------
# AuthenticationService.authenticate_oidc — error paths
# ---------------------------------------------------------------------------

class TestAuthenticateOIDCErrors:

    def test_nack_when_oidc_not_configured(self, mock_user_service):
        svc = AuthenticationService(local=mock_user_service)
        with patch("hestia.domain.auth.service.audit") as mock_audit:
            result = asyncio.run(svc.authenticate_oidc("code", "https://app/callback"))
        assert not result.success
        mock_audit.auth_attempt.assert_called_once_with(
            username="unknown", success=False, source="oidc", reason="oidc_not_configured"
        )

    def test_nack_on_token_exchange_failure(self, auth_service):
        bad_resp = MagicMock()
        bad_resp.raise_for_status.side_effect = req.HTTPError("400")
        with patch("hestia.domain.auth.oidc.requests.post", return_value=bad_resp), \
             patch("hestia.domain.auth.service.audit") as mock_audit:
            result = asyncio.run(auth_service.authenticate_oidc("bad-code", "https://app/callback"))
        assert not result.success
        assert "token exchange" in result.message.lower()
        mock_audit.auth_attempt.assert_called_once_with(
            username="unknown", success=False, source="oidc", reason="token_exchange_failed"
        )

    def test_nack_when_access_token_missing(self, auth_service):
        resp = MagicMock()
        resp.json.return_value = {}
        with patch("hestia.domain.auth.oidc.requests.post", return_value=resp), \
             patch("hestia.domain.auth.service.audit") as mock_audit:
            result = asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))
        assert not result.success
        assert "access_token" in result.message
        mock_audit.auth_attempt.assert_called_once_with(
            username="unknown", success=False, source="oidc", reason="missing_access_token"
        )

    def test_nack_on_userinfo_failure(self, auth_service):
        bad_userinfo = MagicMock()
        bad_userinfo.raise_for_status.side_effect = req.HTTPError("401")
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get", return_value=bad_userinfo), \
             patch("hestia.domain.auth.service.audit") as mock_audit:
            result = asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))
        assert not result.success
        assert "user info" in result.message.lower()
        mock_audit.auth_attempt.assert_called_once_with(
            username="unknown", success=False, source="oidc", reason="userinfo_failed"
        )

    def test_nack_when_email_missing(self, auth_service):
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response(email=None)), \
             patch("hestia.domain.auth.service.audit") as mock_audit:
            result = asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))
        assert not result.success
        assert "email" in result.message.lower()
        mock_audit.auth_attempt.assert_called_once()
        assert mock_audit.auth_attempt.call_args.kwargs["success"] is False
        assert mock_audit.auth_attempt.call_args.kwargs["reason"] == "missing_email"


# ---------------------------------------------------------------------------
# AuthenticationService.authenticate_oidc — success paths
# ---------------------------------------------------------------------------

class TestAuthenticateOIDCSuccess:

    def test_existing_user_returned(self, auth_service, mock_user_service):
        existing_id = uuid.uuid4()
        mock_user_service.repo.get_user_by_email.return_value = {
            "id": existing_id.bytes,
            "username": "alice",
            "first_name": "Alice",
            "last_name": "Dupont",
        }
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response()):
            result = asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))

        assert result.success
        assert result.user_id == existing_id
        assert result.auth_source == "oidc"
        mock_user_service.create_user.assert_not_called()

    def test_new_user_provisioned_with_default_role(self, auth_service, mock_user_service):
        new_id = uuid.uuid4()
        mock_user_service.repo.get_user_by_email.return_value = None
        mock_user_service.create_user.return_value = new_id

        # empty roles list → no mapping match → falls back to ["user"]
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response(roles=[])):
            result = asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))

        assert result.success
        assert result.user_id == new_id
        assert "auto-provisioned" in result.message

        kwargs = mock_user_service.create_user.call_args.kwargs
        assert kwargs["roles"] == ["user"]
        assert kwargs["auth_source"] == "oidc"
        assert kwargs["password"] == "__oidc__"

    def test_new_user_provisioned_with_mapped_role(self, auth_service, mock_user_service):
        new_id = uuid.uuid4()
        mock_user_service.repo.get_user_by_email.return_value = None
        mock_user_service.create_user.return_value = new_id

        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response(roles=["hestia-admin"])):
            result = asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))

        assert result.success
        kwargs = mock_user_service.create_user.call_args.kwargs
        assert "admin" in kwargs["roles"]

    def test_username_falls_back_to_email(self, auth_service, mock_user_service):
        new_id = uuid.uuid4()
        mock_user_service.repo.get_user_by_email.return_value = None
        mock_user_service.create_user.return_value = new_id

        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get",
                   return_value=_userinfo_response(preferred_username=None)):
            asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))

        kwargs = mock_user_service.create_user.call_args.kwargs
        assert kwargs["username"] == "alice@example.com"

    def test_audit_called_for_existing_user(self, auth_service, mock_user_service):
        existing_id = uuid.uuid4()
        mock_user_service.repo.get_user_by_email.return_value = {
            "id": existing_id.bytes,
            "username": "alice",
            "first_name": "Alice",
            "last_name": "Dupont",
        }
        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response()), \
             patch("hestia.domain.auth.service.audit") as mock_audit:
            asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))

        mock_audit.auth_attempt.assert_called_once_with(
            username="alice", success=True, source="oidc"
        )

    def test_audit_called_for_new_user(self, auth_service, mock_user_service):
        new_id = uuid.uuid4()
        mock_user_service.repo.get_user_by_email.return_value = None
        mock_user_service.create_user.return_value = new_id

        with patch("hestia.domain.auth.oidc.requests.post", return_value=_token_response()), \
             patch("hestia.domain.auth.oidc.requests.get", return_value=_userinfo_response(roles=[])), \
             patch("hestia.domain.auth.service.audit") as mock_audit:
            asyncio.run(auth_service.authenticate_oidc("code", "https://app/callback"))

        mock_audit.auth_attempt.assert_called_once_with(
            username="alice", success=True, source="oidc", reason="auto-provisioned"
        )


# ---------------------------------------------------------------------------
# OIDCService.get_logout_url
# ---------------------------------------------------------------------------

class TestGetLogoutUrl:

    def test_points_to_provider_logout_endpoint(self, oidc_service):
        url = oidc_service.get_logout_url("https://app/logged-out")
        assert url.startswith(f"{PROVIDER_URL}/protocol/openid-connect/logout")

    def test_contains_client_id(self, oidc_service):
        url = oidc_service.get_logout_url("https://app/logged-out")
        assert "client_id=hestia-client" in url

    def test_contains_post_logout_redirect_uri(self, oidc_service):
        url = oidc_service.get_logout_url("https://app/goodbye")
        assert "post_logout_redirect_uri=" in url
        assert "goodbye" in url


# ---------------------------------------------------------------------------
# OIDCService.extract_orgs
# ---------------------------------------------------------------------------

class TestExtractOrgs:

    def test_list_claim_mapped(self, oidc_settings):
        oidc_settings.org_claim = "organization"
        oidc_settings.org_mapping = {"acme-corp": "acme"}
        svc = OIDCService(oidc_settings)
        result = svc.extract_orgs({"organization": ["acme-corp"]})
        assert result == ["acme"]

    def test_list_claim_no_mapping(self, oidc_settings):
        oidc_settings.org_claim = "organization"
        oidc_settings.org_mapping = None
        svc = OIDCService(oidc_settings)
        result = svc.extract_orgs({"organization": ["org1", "org2"]})
        assert result == ["org1", "org2"]

    def test_string_claim_returns_list(self, oidc_settings):
        oidc_settings.org_claim = "organization"
        oidc_settings.org_mapping = None
        svc = OIDCService(oidc_settings)
        result = svc.extract_orgs({"organization": "single-org"})
        assert result == ["single-org"]

    def test_missing_claim_returns_empty(self, oidc_service):
        result = oidc_service.extract_orgs({})
        assert result == []

    def test_none_claim_returns_empty(self, oidc_service):
        result = oidc_service.extract_orgs({"organization": None})
        assert result == []
