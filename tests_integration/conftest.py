"""Shared fixtures for the black-box integration suite.

These tests exercise a *running* hestIA instance over HTTP (they are not
unit tests and are not collected by the root pytest.ini, which restricts
default collection to tests/). Run explicitly:

    pytest tests_integration/ -v

See README.md for the full list of environment variables.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import pytest
import requests

BASE_URL = os.environ.get("HESTIA_BASE_URL", "http://localhost:5555").rstrip("/")
ADMIN_USERNAME = os.environ.get("HESTIA_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("HESTIA_ADMIN_PASSWORD", "ChangeMeOnFirstLogin!")

# Endpoints that cause hestIA to call out to the LLM/embedding provider
# (vLLM behind an nginx proxy in this environment, see .env.test.ps1's
# LLM_URL/EMB_URL). Ingestion embeds every chunk; chat/generate/encode call
# the provider directly. Pacing and retrying these specifically - rather
# than every request - keeps auth/CRUD-only tests (the majority of the
# suite) from being needlessly slowed down.
_PROVIDER_PATH_PREFIXES = ("/api/upload", "/api/encode", "/api/chat", "/api/generate")

PROVIDER_CALL_INTERVAL_SECONDS = float(os.environ.get("HESTIA_PROVIDER_CALL_INTERVAL_SECONDS", "2.0"))
PROVIDER_RETRY_ATTEMPTS = int(os.environ.get("HESTIA_PROVIDER_RETRY_ATTEMPTS", "3"))
PROVIDER_RETRY_BACKOFF_SECONDS = float(os.environ.get("HESTIA_PROVIDER_RETRY_BACKOFF_SECONDS", "5.0"))

_provider_call_lock = threading.Lock()
_last_provider_call_at = 0.0


def _is_provider_path(path: str) -> bool:
    return any(path.startswith(p) for p in _PROVIDER_PATH_PREFIXES)


def _throttle_provider_call() -> None:
    """Block until at least PROVIDER_CALL_INTERVAL_SECONDS has passed since
    the last provider-touching call, across the whole test session (pytest
    runs this suite single-threaded/sequential by default, but the lock
    keeps this correct even if that ever changes)."""
    global _last_provider_call_at
    with _provider_call_lock:
        wait = PROVIDER_CALL_INTERVAL_SECONDS - (time.monotonic() - _last_provider_call_at)
        if wait > 0:
            time.sleep(wait)
        _last_provider_call_at = time.monotonic()


def _is_provider_rate_limit_response(resp: requests.Response) -> bool:
    if resp.status_code != 502:
        return False
    try:
        return "429" in resp.json().get("detail", "")
    except Exception:
        return "429" in resp.text


class ApiClient:
    """Thin requests.Session wrapper prefixed with BASE_URL.

    Deliberately does no automatic status-code raising / response parsing —
    each test asserts on the raw Response so failures are explicit and
    traceable to the TST's own expected-outcome bullets.
    """

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        # requests honors HTTP_PROXY/HTTPS_PROXY/etc. from the environment by
        # default; a system/corporate proxy can silently mangle localhost
        # traffic in a way browsers (and PowerShell's Invoke-RestMethod)
        # don't hit, since they use a different proxy-resolution path. A
        # test suite targeting localhost should never go through a proxy
        # regardless of shell env, so disable both explicitly.
        self.session.trust_env = False
        self.session.proxies = {}

    def _url(self, path: str) -> str:
        return path if path.startswith("http") else f"{self.base_url}{path}"

    def set_token(self, token: Optional[str]) -> None:
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            self.session.headers.pop("Authorization", None)

    def get(self, path: str, **kw) -> requests.Response:
        return self.session.get(self._url(path), **kw)

    def post(self, path: str, **kw) -> requests.Response:
        if not _is_provider_path(path):
            return self.session.post(self._url(path), **kw)

        # Files (multipart uploads) are file handles that get consumed on
        # the first attempt - re-open-and-retry is the caller's problem for
        # /api/upload specifically; retry here still helps every other
        # provider path (encode/chat/generate), which are all json= bodies.
        can_retry = "files" not in kw
        attempts = PROVIDER_RETRY_ATTEMPTS if can_retry else 1

        last_resp = None
        for attempt in range(attempts):
            _throttle_provider_call()
            resp = self.session.post(self._url(path), **kw)
            if not _is_provider_rate_limit_response(resp):
                return resp
            last_resp = resp
            if attempt < attempts - 1:
                time.sleep(PROVIDER_RETRY_BACKOFF_SECONDS * (attempt + 1))
        return last_resp

    def patch(self, path: str, **kw) -> requests.Response:
        return self.session.patch(self._url(path), **kw)

    def put(self, path: str, **kw) -> requests.Response:
        return self.session.put(self._url(path), **kw)

    def delete(self, path: str, **kw) -> requests.Response:
        return self.session.delete(self._url(path), **kw)


def login(client: ApiClient, username: str, password: str) -> requests.Response:
    """POST /login — OAuth2PasswordRequestForm shape, form-urlencoded."""
    return client.post("/login", data={"username": username, "password": password})


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def admin_client() -> ApiClient:
    client = ApiClient()
    resp = login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert resp.status_code == 200, (
        f"Seeded admin login failed ({resp.status_code}): {resp.text}\n"
        f"Set HESTIA_ADMIN_USERNAME/HESTIA_ADMIN_PASSWORD if the instance "
        f"under test uses different credentials than the .env.test.ps1 default."
    )
    client.set_token(resp.json()["access_token"])
    return client


@dataclass
class TestUser:
    user_id: str
    username: str
    password: str
    client: ApiClient = field(default_factory=ApiClient)

    def login(self) -> requests.Response:
        resp = login(self.client, self.username, self.password)
        if resp.status_code == 200:
            self.client.set_token(resp.json()["access_token"])
        return resp


def _role_id_map(admin_client: ApiClient) -> dict:
    """GET /admin/roles -> {name: id}. CreateUserRequest.roles is typed
    list[int] (hestia/api/schemas/requests.py:76) - it wants role IDs, not
    names, even though the service layer underneath would accept either.
    IDs are auto-increment, not fixed, so this must be looked up per
    instance rather than hardcoded. Only "admin" and "user" are seeded as
    system roles (hestia/infrastructure/db/user_repository.py:142-146) -
    "moderator" is a per-tenant membership attribute, not a role here."""
    resp = admin_client.get("/admin/roles")
    assert resp.status_code == 200, f"role lookup failed: {resp.status_code} {resp.text}"
    body = resp.json()
    rows = body.get("roles", body) if isinstance(body, dict) else body
    return {r["name"]: r["id"] for r in rows}


@pytest.fixture
def make_user(admin_client: ApiClient):
    """Factory fixture: create a disposable user via POST /admin/users/create.

    Returns a callable so a single test can create more than one user
    (e.g. two roles). Every created user is deleted at teardown.
    """
    created: list[str] = []
    role_ids = _role_id_map(admin_client)

    def _make(
        *,
        roles: Optional[list[str]] = None,
        organization: Optional[str] = None,
        expires_at: Optional[str] = None,
        password: Optional[str] = None,
    ) -> TestUser:
        suffix = uuid.uuid4().hex[:10]
        username = f"it-{suffix}"
        pw = password or f"Pw!{uuid.uuid4().hex[:12]}A1"
        role_names = roles or ["user"]
        body = {
            "username": username,
            "email": f"{username}@example.invalid",
            "password": pw,
            "first_name": "Integration",
            "last_name": "Test",
            "roles": [role_ids[name] for name in role_names],
            "organization": organization,
            "expires_at": expires_at,
        }
        resp = admin_client.post("/admin/users/create", json=body)
        assert resp.status_code == 200, f"user create failed: {resp.status_code} {resp.text}"
        user_id = resp.json()["user_id"]
        created.append(user_id)
        return TestUser(user_id=user_id, username=username, password=pw)

    yield _make

    for uid in created:
        admin_client.delete(f"/admin/users/user/{uid}")


@pytest.fixture
def make_org(admin_client: ApiClient):
    """Factory fixture: create a disposable organization/tenant."""
    created: list[str] = []

    def _make(name: Optional[str] = None) -> dict:
        suffix = uuid.uuid4().hex[:8]
        org_name = name or f"IT-Org-{suffix}"
        resp = admin_client.post(
            "/admin/organizations/create",
            json={"name": org_name, "abbreviation": suffix.upper()[:6]},
        )
        assert resp.status_code == 200, f"org create failed: {resp.status_code} {resp.text}"
        # POST /admin/organizations/create only returns {"ok": true}
        # (hestia/api/routers/admin.py:181-197) - no id, so look the new org
        # up by name via the list endpoint instead.
        listing = admin_client.get("/admin/organizations")
        assert listing.status_code == 200, f"org lookup failed: {listing.status_code} {listing.text}"
        orgs = listing.json().get("organizations", [])
        matches = [o for o in orgs if o.get("name") == org_name]
        assert matches, f"created org {org_name!r} not found in listing: {orgs}"
        org = matches[0]
        created.append(str(org["id"]))
        return org

    yield _make

    for org_id in created:
        admin_client.delete(f"/admin/organizations/{org_id}")


@pytest.fixture
def make_collection(admin_client: ApiClient):
    """Factory fixture: create a disposable collection (no documents)."""
    created: list[str] = []

    def _make(owner_org_id: Optional[int] = None) -> str:
        name = f"it-col-{uuid.uuid4().hex[:10]}"
        resp = admin_client.post(
            "/admin/collections/create",
            json={"name": name, "owner_org_id": owner_org_id},
        )
        assert resp.status_code == 200, f"collection create failed: {resp.status_code} {resp.text}"
        created.append(name)
        return name

    yield _make

    for name in created:
        admin_client.delete(f"/api/collections/{name}")


@pytest.fixture
def make_queryable_collection(admin_client: ApiClient, make_org, make_collection, make_user):
    """Factory fixture: create a collection owned by a tenant, plus a
    regular user who is a member of that tenant.

    RAG queries (/api/chat, /api/generate) are gated by CollectionAccessPolicy
    (hestia/domain/policies/guard.py), which checks the *querying user's own*
    tenant-based allowed_collections - there is no admin bypass there (unlike
    can_read_collection, used by /api/search and listing endpoints, which
    does bypass for is_admin). So exercising chat/generate against a
    collection requires a real tenant member, not just an admin token.
    """

    def _make() -> tuple:
        org = make_org()
        org_id = org["id"]
        collection = make_collection(owner_org_id=org_id)

        member = make_user(roles=["user"])
        add_member = admin_client.post(f"/admin/organizations/{org_id}/members/{member.user_id}")
        assert add_member.status_code == 200, add_member.text

        resp = member.login()
        assert resp.status_code == 200, resp.text
        return collection, member

    return _make


def upload_fixture(
    admin_client: ApiClient,
    collection: str,
    fixture_path: str,
    *,
    metadata_overrides: Optional[dict] = None,
    language: str = "english",
) -> requests.Response:
    """POST /api/upload a fixture file from docs/specs/tst/assets/."""
    import json as _json

    with open(fixture_path, "rb") as fh:
        files = {"file": (os.path.basename(fixture_path), fh)}
        data = {
            "collection": collection,
            "language": language,
            "metadata_overrides": _json.dumps(metadata_overrides or {}),
        }
        return admin_client.post("/api/upload", files=files, data=data)


@pytest.fixture
def make_collection_with_doc(admin_client: ApiClient, make_collection):
    """Factory fixture: create a collection and ingest one fixture document."""

    def _make(fixture_path: str, *, metadata_overrides: Optional[dict] = None) -> str:
        collection = make_collection()
        resp = upload_fixture(admin_client, collection, fixture_path, metadata_overrides=metadata_overrides)
        assert resp.status_code == 200, f"upload failed: {resp.status_code} {resp.text}"
        return collection

    return _make


def encode_dense(client: ApiClient, text: str) -> list:
    resp = client.post("/api/encode", json={"type": "dense", "input": text})
    assert resp.status_code == 200, f"dense encode failed: {resp.status_code} {resp.text}"
    return resp.json()["vector"]


def encode_sparse(client: ApiClient, text: str, collection: str) -> dict:
    resp = client.post("/api/encode", json={"type": "sparse", "input": text, "collection": collection})
    assert resp.status_code == 200, f"sparse encode failed: {resp.status_code} {resp.text}"
    return resp.json()["vector"]


def search_text(client: ApiClient, collection: str, text: str, mode: str = "semantic") -> requests.Response:
    """POST /api/search wants pre-computed vectors, not raw text
    (hestia/api/routers/search.py) - this drives POST /api/encode first and
    shapes the query the way that router expects for each mode.
    """
    if mode == "semantic":
        query = encode_dense(client, text)
    elif mode == "keyword":
        query = encode_sparse(client, text, collection)
    elif mode == "hybrid":
        query = {
            "dense": encode_dense(client, text),
            "sparse": encode_sparse(client, text, collection),
        }
    else:
        raise ValueError(f"unsupported mode: {mode}")

    return client.post("/api/search", json={"mode": mode, "query": query, "collection": collection})


ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "specs", "tst", "assets",
)
