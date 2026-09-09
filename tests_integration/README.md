# Integration test suite

Black-box tests that exercise a **running** hestIA instance over its REST API — one
script per automated TST item (`docs/reqs/tst/TST-0XX.yml`, `execution_type: Automated`).
Each file's docstring cites the TST it verifies and its "Expected outcome" bullets.

This directory is deliberately **not** under `tests/` (which `pytest.ini` restricts
default collection to), so a bare `pytest` from the repo root — including the
GitLab CI unit/coverage job — never touches it. Run it explicitly:

```
pytest tests_integration/ -v
```

against a live instance (e.g. `docker compose up -d`).

## Required environment variables

| Variable | Default | Purpose |
|---|---|---|
| `HESTIA_BASE_URL` | `http://localhost:5555` | Base URL of the running backend |
| `HESTIA_ADMIN_USERNAME` | `admin` | Seeded admin username (matches `.env.test.ps1`) |
| `HESTIA_ADMIN_PASSWORD` | `ChangeMeOnFirstLogin!` | Seeded admin password |

## Optional environment variables (tests skip cleanly without them)

| Variable | Used by | Purpose |
|---|---|---|
| `HESTIA_LDAP_TEST_USERNAME` / `HESTIA_LDAP_TEST_PASSWORD` | TST-005, TST-008 | Credentials for a test user in a reachable LDAP directory the instance is configured against (`AUTH_MODE=ldap`) |
| `HESTIA_LDAP_TEST_ROLE` | TST-008 | Expected hestIA role for the above user, per `LDAP_GROUP_MAPPING` |
| `HESTIA_LDAP_TEST_GROUP2_USERNAME` / `_PASSWORD` / `_ROLE` | TST-008 | A second LDAP test user in a *different* mapped group |
| `HESTIA_AUTH_MAX_ATTEMPTS` | TST-012 | Must match the instance's configured `AUTH_MAX_ATTEMPTS` (default 5) |
| `HESTIA_AUTH_LOCKOUT_SECONDS` | TST-012 | Must match the instance's `AUTH_LOCKOUT_DURATION` in seconds; the "wait it out" half of this test is skipped if this is > 180s (too slow for a normal test run) |
| `HESTIA_AUTH_TOKEN_LIFETIME_SECONDS` | TST-013 | Must match the instance's `AUTH_TOKEN_LIFETIME` in seconds; the natural-expiry half of this test is skipped unless set to a short value (<=180s) |
| `HESTIA_LARGE_CORPUS_DIR` | TST-034 | Path to a representative/synthetic corpus (target: >=100 GB). Not exercised by default. |
| `HESTIA_LARGE_CORPUS_RESPONSE_MS` | TST-034 | Response-time threshold in ms (default 5000) |
| `HESTIA_LARGE_CORPUS_TEST_QUERY` | TST-034 | Query text to run against the corpus (default `"policy"`) |
| `HESTIA_PROVIDER_CALL_INTERVAL_SECONDS` | all provider-touching tests | Minimum spacing enforced between calls to `/api/upload`, `/api/encode`, `/api/chat`, `/api/generate` (default 2.0s) - see below |
| `HESTIA_PROVIDER_RETRY_ATTEMPTS` | same | How many times to retry a provider call that comes back `502 "Provider returned 429"` (default 3, i.e. 2 retries) |
| `HESTIA_PROVIDER_RETRY_BACKOFF_SECONDS` | same | Backoff unit between retries, multiplied by attempt number (default 5.0s, so 5s/10s) |

## Pacing calls to the LLM/embedding provider

`/api/upload`, `/api/encode`, `/api/chat`, and `/api/generate` all cause hestIA to call
out to the LLM/embedding provider (vLLM behind an nginx proxy per `.env.test.ps1`'s
`LLM_URL`/`EMB_URL`) - `ApiClient.post` (`conftest.py`) automatically paces these
specifically (not every request, so auth/CRUD-only tests aren't slowed down) to at most
one every `HESTIA_PROVIDER_CALL_INTERVAL_SECONDS`, and retries with backoff on a
`502 "Provider returned 429"` response (up to `HESTIA_PROVIDER_RETRY_ATTEMPTS` total
tries). This is shared, external infrastructure - if you're still seeing `502`s after a
run, raise the interval/retry values rather than assume something's broken.

`/api/upload` calls are paced the same way but are **not** retried on a 502 - every
test opens its fixture file in a `with open(...)` block that's exhausted after the
first send, so a blind retry would just resubmit an empty body. If uploads start
showing up in the 502s, the fix is to give upload calls their own retry path that
reopens the file per attempt, not to reuse this one.

## The shared "admin" login budget

`POST /login` is rate-limited **per submitted username, across all requests to it —
not just failures** (`hestia/api/limiter.py`, default `5 per 5 minutes`, configurable
via `AUTH_MAX_ATTEMPTS`/`AUTH_LOCKOUT_DURATION`). Every test that authenticates as the
shared admin account draws from that same budget: the `admin_client` session fixture (1
call, shared by ~20 tests) plus TST-004's two calls (valid + invalid login, each a
distinct scenario that must make its own request) plus TST-007's one call = 4 total in
a normal run, safely under 5. Manual checks against the same instance (curl,
`Invoke-RestMethod`, a browser login) count against the *same* budget.

If you hit `429 Rate limit exceeded` — including from `admin_client`'s single call,
which then cascades to every dependent test as a cached setup failure — it means that
budget was already consumed before the run started (a previous run, a manual login
check, etc.), not that the suite itself is broken. Wait out the window (default 5 min)
or restart the backend process (the limiter is in-memory) before re-running.

## Known gaps (found while writing these scripts, not something this suite works around)

- **TST-014**'s "tenant-role grant with a future `starts_at`" scenario is `pytest.mark.skip`ped:
  no admin API sets a role grant's `starts_at` — `UserService.create_user` and `update_user`
  (`hestia/domain/auth/users.py`) both hardcode it to "now". `user_roles.starts_at` exists at the
  DB layer with nothing above it exposing it. This is a real gap between SRS-005's time-bounded-access
  criterion and the current API surface.
- **TST-035** (Help Content Management) has no script here at all — `hestia/api/routers/help.py`
  doesn't exist and isn't in the router registry, only a stale compiled `__pycache__` file remains.
  Flagged for a separate follow-up (re-scope the requirement, or re-mark the TST) rather than
  scripted against a nonexistent endpoint.

## Assumptions worth double-checking against a real running instance

A few response-body field names (`/api/chat`'s exact JSON shape, whether `query_kwargs.mode`
threads through to the retrieval call for TST-042) were inferred from route/schema source rather
than an observed live response, since no instance was available while writing these. Each such
spot is commented in-line. If a test fails on a field-name mismatch rather than a real behavior
gap, that's very likely why — adjust the extraction, not the underlying assertion.
