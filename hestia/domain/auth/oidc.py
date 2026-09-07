from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlencode

import requests

from hestia.config.settings import OIDCSettings

_log = logging.getLogger("hestia.system")


class OIDCService:

    def __init__(self, settings: OIDCSettings):
        self.settings = settings
        base = settings.provider_url.rstrip("/")
        self._auth_url = f"{base}/protocol/openid-connect/auth"
        self._token_url = f"{base}/protocol/openid-connect/token"
        self._userinfo_url = f"{base}/protocol/openid-connect/userinfo"

    def get_authorization_url(self, redirect_uri: str, state: str, code_challenge: str | None = None) -> str:
        params = {
            "client_id": self.settings.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.settings.scopes),
            "state": state,
        }
        if code_challenge:
            # PKCE -- hardening against authorization-code interception. Not
            # load-bearing for this app's confidential client (it holds a
            # client_secret already), but cheap and standard to add.
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        return f"{self._auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> dict:
        # requests is blocking; called from an async route (auth.py's
        # oidc_callback) via AuthenticationService.authenticate_oidc, so this
        # runs off the event loop rather than stalling every other in-flight
        # request for the duration of the round trip to the IdP.
        def _call() -> dict:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            }
            if code_verifier:
                data["code_verifier"] = code_verifier
            resp = requests.post(self._token_url, data=data, timeout=10)
            resp.raise_for_status()
            return resp.json()

        return await asyncio.to_thread(_call)

    async def get_user_info(self, access_token: str) -> dict:
        def _call() -> dict:
            resp = requests.get(
                self._userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()

        return await asyncio.to_thread(_call)

    def get_logout_url(self, post_logout_redirect_uri: str) -> str:
        base = self.settings.provider_url.rstrip("/")
        params = {
            "client_id": self.settings.client_id,
            "post_logout_redirect_uri": post_logout_redirect_uri,
        }
        return f"{base}/protocol/openid-connect/logout?{urlencode(params)}"

    def extract_orgs(self, user_info: dict) -> list[str]:
        claim = user_info.get(self.settings.org_claim)
        raw: list[str] = []
        if isinstance(claim, list):
            raw = [str(o) for o in claim]
        elif isinstance(claim, str):
            raw = [claim]
        if self.settings.org_mapping:
            raw = [self.settings.org_mapping.get(o, o) for o in raw]
        return raw

    def extract_roles(self, user_info: dict) -> list[str]:
        claim = user_info.get(self.settings.role_claim)
        if isinstance(claim, list):
            return [str(r) for r in claim]
        if isinstance(claim, str):
            return [claim]
        return []
