from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from hestia.api.dependencies import get_container
from hestia.api.limiter import limiter, login_rate_limit
from hestia.api.routers.auth import router
from hestia.api.security import create_access_token, get_current_user, oauth2_scheme
from hestia.domain.auth.models import AuthResult


def _app(container=None):
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: (container or MagicMock())
    return app


def _failing_auth():
    auth = MagicMock()
    auth.authenticate.return_value = AuthResult.nack()
    return auth


@pytest.fixture(autouse=True)
def _reset_limiter():
    login_rate_limit.configure(max_attempts=3, window_minutes=1)
    limiter.reset()
    yield
    limiter.reset()


class TestLoginRateLimiting:

    def test_repeated_failed_logins_for_one_account_get_locked_out(self):
        container = MagicMock()
        container.services.get.return_value = _failing_auth()
        client = TestClient(_app(container))

        statuses = [
            client.post("/login", data={"username": "alice", "password": "wrong"}).status_code
            for _ in range(4)
        ]
        assert statuses[:3] == [401, 401, 401]
        assert statuses[3] == 429

    def test_lockout_does_not_affect_a_different_account(self):
        # Regression test: the limiter used to key off source IP, and every
        # browser login is proxied through hestia-ui's server, so all real
        # users share one IP as seen by this backend -- one account's
        # failed attempts must not lock out a different account.
        container = MagicMock()
        container.services.get.return_value = _failing_auth()
        client = TestClient(_app(container))

        for _ in range(3):
            client.post("/login", data={"username": "alice", "password": "wrong"})
        locked_out = client.post("/login", data={"username": "alice", "password": "wrong"})
        assert locked_out.status_code == 429

        bob_resp = client.post("/login", data={"username": "bob", "password": "wrong"})
        assert bob_resp.status_code == 401  # not 429 — bob has his own bucket


class TestLoginSuccess:

    def test_successful_login_returns_token(self):
        container = MagicMock()
        auth = MagicMock()
        auth.authenticate.return_value = AuthResult(
            success=True, message="ok", user_id=uuid.uuid4(), must_change_pw=False,
        )
        auth.config.token_secret_key = "x" * 32
        auth.config.token_encoding_alg = "HS256"
        auth.config.token_lifetime_minutes = 360
        auth.local.repo.record_login = MagicMock()
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.post("/login", data={"username": "alice", "password": "correct"})

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"


class TestLogout:

    def test_audits_logout_and_returns_ok(self):
        container = MagicMock()
        auth = MagicMock()
        auth.config.token_secret_key = "x" * 32
        auth.config.token_encoding_alg = "HS256"
        container.services.get.return_value = auth
        user = MagicMock()
        user.id = uuid.uuid4()
        user.username = "alice"
        user.auth_source = "local"
        token = create_access_token(user.id, key="x" * 32, algorithm="HS256")

        app = _app(container)
        app.dependency_overrides[get_current_user] = lambda: user
        client = TestClient(app)

        resp = client.post("/logout", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        auth.audit_logout.assert_called_once_with(
            user_id=str(user.id), username="alice", source="local"
        )

    def test_revokes_this_tokens_jti(self):
        # A copy of this exact token captured before logout (XSS, a log
        # leak, a compromised proxy) must not keep working afterward --
        # confirms logout actually revokes the token it was called with,
        # not just some hardcoded/placeholder value.
        container = MagicMock()
        auth = MagicMock()
        auth.config.token_secret_key = "x" * 32
        auth.config.token_encoding_alg = "HS256"
        container.services.get.return_value = auth
        user = MagicMock()
        user.id = uuid.uuid4()
        user.username = "alice"
        user.auth_source = "local"
        token = create_access_token(user.id, key="x" * 32, algorithm="HS256")
        import jwt as _jwt
        expected_jti = _jwt.decode(token, key="x" * 32, algorithms=["HS256"])["jti"]

        app = _app(container)
        app.dependency_overrides[get_current_user] = lambda: user
        client = TestClient(app)

        client.post("/logout", headers={"Authorization": f"Bearer {token}"})

        auth.local.repo.revoke_token.assert_called_once()
        assert auth.local.repo.revoke_token.call_args.kwargs["jti"] == expected_jti

    def test_no_auth_service_still_returns_ok(self):
        # If the "auth" service isn't registered there's nothing to audit
        # or revoke against, but logout must not fail for the caller.
        container = MagicMock()
        container.services.get.return_value = None
        user = MagicMock()
        user.id = uuid.uuid4()
        user.username = "alice"
        user.auth_source = "local"

        app = _app(container)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[oauth2_scheme] = lambda: "unused-token"
        client = TestClient(app)

        resp = client.post("/logout")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestOidcAuthorize:

    def test_returns_authorization_url_and_state(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.oidc.settings.redirect_uri_allowlist = []
        auth.oidc.get_authorization_url.return_value = "https://idp/authorize?x=1"
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/authorize", params={"redirect_uri": "https://app/callback"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["url"] == "https://idp/authorize?x=1"
        assert "state" in body
        auth.oidc.get_authorization_url.assert_called_once()
        _, kwargs = auth.oidc.get_authorization_url.call_args
        assert kwargs["redirect_uri"] == "https://app/callback"
        assert kwargs["state"] == body["state"]

    def test_returns_400_when_auth_service_missing(self):
        container = MagicMock()
        container.services.get.return_value = None
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/authorize", params={"redirect_uri": "https://app/callback"})

        assert resp.status_code == 400

    def test_returns_400_when_oidc_not_configured(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = None
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/authorize", params={"redirect_uri": "https://app/callback"})

        assert resp.status_code == 400

    def test_redirect_uri_outside_configured_allowlist_is_rejected(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.oidc.settings.redirect_uri_allowlist = ["https://app/callback"]
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/authorize", params={"redirect_uri": "https://evil.example/steal"})

        assert resp.status_code == 400
        auth.oidc.get_authorization_url.assert_not_called()

    def test_redirect_uri_inside_configured_allowlist_is_permitted(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.oidc.settings.redirect_uri_allowlist = ["https://app/callback"]
        auth.oidc.get_authorization_url.return_value = "https://idp/authorize?x=1"
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/authorize", params={"redirect_uri": "https://app/callback"})

        assert resp.status_code == 200

    def test_returns_a_pkce_code_verifier_and_passes_challenge_downstream(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.oidc.settings.redirect_uri_allowlist = []
        auth.oidc.get_authorization_url.return_value = "https://idp/authorize?x=1"
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/authorize", params={"redirect_uri": "https://app/callback"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["code_verifier"]
        _, kwargs = auth.oidc.get_authorization_url.call_args
        assert kwargs["code_challenge"]
        assert kwargs["code_challenge"] != body["code_verifier"]  # a hash, not the raw verifier


class TestOidcLogout:

    def test_redirects_to_oidc_logout_url(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.oidc.settings.redirect_uri_allowlist = []
        auth.oidc.get_logout_url.return_value = "https://idp/logout?x=1"
        container.services.get.return_value = auth
        client = TestClient(_app(container), follow_redirects=False)

        resp = client.get("/auth/oidc/logout", params={"redirect_uri": "https://app/"})

        assert resp.status_code == 302
        assert resp.headers["location"] == "https://idp/logout?x=1"
        auth.oidc.get_logout_url.assert_called_once_with("https://app/")

    def test_redirect_uri_outside_configured_allowlist_is_rejected(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.oidc.settings.redirect_uri_allowlist = ["https://app/"]
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/logout", params={"redirect_uri": "https://evil.example/"})

        assert resp.status_code == 400
        auth.oidc.get_logout_url.assert_not_called()

    def test_returns_400_when_auth_service_missing(self):
        container = MagicMock()
        container.services.get.return_value = None
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/logout", params={"redirect_uri": "https://app/"})

        assert resp.status_code == 400

    def test_returns_400_when_oidc_not_configured(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = None
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.get("/auth/oidc/logout", params={"redirect_uri": "https://app/"})

        assert resp.status_code == 400


class TestOidcCallback:

    def test_returns_400_when_auth_service_missing(self):
        container = MagicMock()
        container.services.get.return_value = None
        client = TestClient(_app(container))

        resp = client.post(
            "/auth/oidc/callback",
            json={"code": "abc", "redirect_uri": "https://app/callback"},
        )

        assert resp.status_code == 400

    def test_returns_400_when_oidc_not_configured(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = None
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.post(
            "/auth/oidc/callback",
            json={"code": "abc", "redirect_uri": "https://app/callback"},
        )

        assert resp.status_code == 400

    def test_awaits_authenticate_oidc_and_issues_token(self):
        # Regression test: authenticate_oidc became async (to move OIDC's
        # HTTP calls off the event loop) — the route must await it rather
        # than treating the coroutine object itself as a truthy result.
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.authenticate_oidc = AsyncMock(return_value=AuthResult(
            success=True, message="ok", user_id=uuid.uuid4(), must_change_pw=0,
        ))
        auth.config.token_secret_key = "x" * 32
        auth.config.token_encoding_alg = "HS256"
        auth.config.token_lifetime_minutes = 360
        auth.local.repo.record_login = MagicMock()
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.post(
            "/auth/oidc/callback",
            json={"code": "abc", "redirect_uri": "https://app/callback", "state": "xyz"},
        )

        assert resp.status_code == 200
        assert "access_token" in resp.json()
        auth.authenticate_oidc.assert_awaited_once_with("abc", "https://app/callback", code_verifier=None)

    def test_failed_oidc_authentication_returns_401(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.authenticate_oidc = AsyncMock(return_value=AuthResult.nack("bad code"))
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.post(
            "/auth/oidc/callback",
            json={"code": "bad", "redirect_uri": "https://app/callback", "state": "xyz"},
        )

        assert resp.status_code == 401

    def test_missing_state_is_rejected(self):
        # The frontend BFF always supplies the state it validated against its
        # own cookie; a caller that omits it entirely is skipping that check
        # rather than just failing it, so this is a hard 400, not a 401.
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.authenticate_oidc = AsyncMock(return_value=AuthResult(
            success=True, message="ok", user_id=uuid.uuid4(), must_change_pw=0,
        ))
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.post("/auth/oidc/callback", json={"code": "abc", "redirect_uri": "https://app/callback"})

        assert resp.status_code == 400
        auth.authenticate_oidc.assert_not_awaited()

    def test_forwards_code_verifier_to_authenticate_oidc(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        auth.authenticate_oidc = AsyncMock(return_value=AuthResult(
            success=True, message="ok", user_id=uuid.uuid4(), must_change_pw=0,
        ))
        auth.config.token_secret_key = "x" * 32
        auth.config.token_encoding_alg = "HS256"
        auth.config.token_lifetime_minutes = 360
        auth.local.repo.record_login = MagicMock()
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        client.post(
            "/auth/oidc/callback",
            json={
                "code": "abc", "redirect_uri": "https://app/callback",
                "state": "xyz", "code_verifier": "verifier-abc",
            },
        )

        auth.authenticate_oidc.assert_awaited_once_with(
            "abc", "https://app/callback", code_verifier="verifier-abc",
        )

    def test_blank_state_is_rejected(self):
        container = MagicMock()
        auth = MagicMock()
        auth.oidc = MagicMock()
        container.services.get.return_value = auth
        client = TestClient(_app(container))

        resp = client.post(
            "/auth/oidc/callback",
            json={"code": "abc", "redirect_uri": "https://app/callback", "state": ""},
        )

        assert resp.status_code == 400
