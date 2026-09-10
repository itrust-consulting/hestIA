# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

hestIA is an on-premises enterprise RAG assistant: a FastAPI backend (`hestia/`) plus a
SvelteKit frontend (`hestia-ui/`). It grounds LLM responses in an access-controlled,
classification-aware document corpus (Qdrant) and produces an audit trail of security-relevant
actions. Development here is driven by a formal, Doorstop-based requirements/test process — see
"Requirements traceability" below before assuming code is the only source of truth.

## Commands

### Backend (Python 3.13, from repo root)

```bash
pip install -r requirements.txt -r requirements-dev.txt   # requirements-dev adds pytest/pytest-cov
python -m hestia.main                                      # run the API (no --reload; restart after edits)

pytest                                                      # unit tests (tests/ only, per pytest.ini)
pytest tests/unit/api/routers/test_admin.py -q              # single file
pytest tests/unit/api/routers/test_admin.py::TestUpdateUser::test_admin_updates_user  # single test
pytest --cov=hestia --cov-report=term-missing --cov-fail-under=90   # matches CI gate (.gitlab-ci.yml)

pytest tests_integration/ -v                                # black-box tests against a LIVE instance only
```

`tests_integration/` is excluded from default collection on purpose (it needs a running backend
plus real LDAP/OIDC/LLM/Qdrant endpoints — see `tests_integration/README.md` and `.env.test.ps1`
for required env vars). Don't run it as a substitute for `pytest`. Its README also documents that
`POST /login` shares one rate-limit budget across the whole suite (default 5 attempts/5 min per
username, `hestia/api/limiter.py`) — a stray manual login against the same instance can starve it.

No Python linter/formatter is configured (no ruff/flake8/mypy/black config in the repo) — don't
invent lint commands.

### Frontend (`hestia-ui/`, Node + npm)

```bash
npm install
npm run dev            # vite dev server; proxies to the backend via PRIVATE_MICROSERVICE_URL
npm run build
npm run check          # svelte-kit sync + svelte-check (type checking)
npm run test           # vitest run (jsdom environment)
npm run test:watch
```

The README's env var table lists `PUBLIC_MICROSERVICE_URL` for the backend URL — the actual
variable read by `src/lib/server/backend.ts` and the SvelteKit `api/*` routes is
**`PRIVATE_MICROSERVICE_URL`** (server-only, via `$env/dynamic/private`); `PUBLIC_AUTH_MODE` and
`PUBLIC_APP_VERSION` are the only real client-exposed vars. Don't trust the README's env tables
without cross-checking `hestia/config/settings.py` (backend) or a `grep` of `env.PUBLIC_*` /
`env.*` (frontend) — this project's own `docs/icd.md` revision history documents several other
places where the docs had drifted from the implementation.

## Architecture

### Backend layers (`hestia/`)

```
api/            FastAPI routers, Pydantic schemas, JWT security (api/security.py), rate limiting (api/limiter.py)
application/    Document ingestion pipeline (parse -> chunk -> embed -> index)
domain/         RAG execution graph, auth services, access policies -- framework-agnostic
infrastructure/ LLM providers (vLLM/Ollama), DB providers (Qdrant, SQLite), parsers, logging
config/         Settings, all loaded from env vars in one place (Settings.load())
container.py    Composition root: wires config -> providers -> services once at startup
```

`hestia/main.py`'s `lifespan` is the only place startup order matters: `Settings.load()` →
`setup_logging()` → `build_container()`. Services are conditionally registered based on which
LLM/DB connections are configured (`hestia/api/routers/registry.py`); an unconfigured service's
routes are never mounted, so calling them 404s rather than 403s or 500s — check `GET /ready` to
see what's actually wired before assuming a 404 is a routing bug.

`/health`, `/ready`, and `/models` (`hestia/api/routers/health.py`) are unauthenticated **by
design**, for orchestrator/load-balancer probing — this is a documented, accepted decision
(`docs/icd.md` §4.14, `docs/sdd.md` §5.4/§12.2), not an oversight. Don't "fix" this by adding auth
without reading those sections first.

### RAG execution model

Chat/generate/RAG requests aren't hardcoded call chains — `RequestHandler.resolve()`
(`hestia/handler.py`) builds an execution graph from YAML templates (`hestia/domain/rag/graph.py`,
`templater.py`) and runs it node-by-node (encode → retrieve → augment → generate). Templates live
in two places with different lifecycles:

- `hestia/templates/base/*.yaml` — coupled to the Runner's node handlers, always re-copied from
  source to `app/data/templates/base` on startup (never admin-editable).
- `hestia/templates/workflows/*.yaml` — **seeded once** into `app/data/templates/workflows` and
  then left alone (`hestia/domain/rag/template_sync.py`): a file already present there is never
  overwritten from source. Editing a file under `hestia/templates/workflows/` has **no effect**
  on an existing `app/data` (dev checkout or deployment) — you must also copy the change into
  `app/data/templates/workflows/` (or delete the stale file there so it reseeds on next startup).
  Admin edits made through `hestia/api/routers/workflow_settings.py` live only in `app/data` and
  survive restarts for the same reason. Also note uvicorn runs without `--reload`
  (`hestia/main.py`), so any backend code change needs a manual restart regardless.

Access control on a RAG request goes through `hestia/domain/policies/guard.py`'s
`ExecutionPolicy` (currently one policy, `CollectionAccessPolicy`), which derives a
server-side `max_classification` filter from the user's own permissions — never trust a
classification filter supplied by the client for any new retrieval-adjacent endpoint; derive it
from `ExecutionPolicy.check()` the same way `handler.py` and `api/routers/search.py` do.

### Audit logging

`hestia/infrastructure/logging/audit.py` is a typed facade (`audit = AuditLogger()`) over a
dedicated `hestia.audit` logger — every method is one auditable event class, fire-and-forget,
metadata only (never raw prompt/response content). `hestia/infrastructure/logging/config.py`
writes `audit.log` and `system.log` as physically separate handlers; lowering the general log
level cannot silence `audit.log`. Login/logout auditing (`auth_attempt`) is additionally gated by
`AuthSettings.audit_logs` (`AUTH_AUDIT_LOGS` env var, **off by default**) — code that reads the
"failed logins" counter or reasons about the audit trail should account for this being disabled
on a fresh install.

### Auth

Three modes (`AUTH_MODE`: `local` | `ldap` | `oidc`), unified behind
`AuthenticationService` (`hestia/domain/auth/service.py`). JWTs are HMAC-signed
(`api/security.py` explicitly restricts `jwt.decode`'s `algorithms=` to a fixed allow-list — never
pass a config-derived algorithm string through unchecked). `api/limiter.py`'s login lockout is
keyed by **submitted username**, not source IP, because every browser login is proxied through
`hestia-ui`'s server-side routes and would otherwise collapse every real user onto one IP.

### Frontend: BFF pattern, not a plain SPA (`hestia-ui/`)

`hestia-ui` is a SvelteKit **backend-for-frontend**: the JWT lives in an httpOnly cookie, never
sent to the browser JS. `src/hooks.server.ts` fetches `/account` from the Python backend on every
request to hydrate `event.locals.user`, and does a defense-in-depth role check for
`/api/admin/*` (the backend re-checks authorization independently — this hook is not the
enforcement point). Routes under `src/routes/api/*` are thin server-side proxies
(`src/lib/server/backend.ts`'s `backendFetch`) to the FastAPI backend at
`PRIVATE_MICROSERVICE_URL`; `src/routes/(protected)/*` are the actual pages. CSRF/CSP are
explicitly configured in `svelte.config.js` (empty `trustedOrigins`, nonce-based CSP) as the
*only* CSRF defense on state-changing routes — there's no separate anti-CSRF token scheme.

### Requirements traceability (Doorstop)

`docs/reqs/` is a [Doorstop](https://doorstop.readthedocs.io/) item tree, not just prose:
`MRS` (master requirements) → `SRS` (software requirements, `parent: MRS`) → `TST` (test cases,
`parent: SRS`) → `TRP` (test reports/review findings, `parent: TST`), plus a separate `GDPR` tree.
Each `.yml` item has `text`, `links`, `normative`, `reviewed` (a content hash), etc. Source code
cross-references these with `# @MRS-XXX` comments (e.g. `hestia/api/security.py`,
`hestia/api/routers/admin.py`) — when a change affects behavior a requirement describes, check
whether the corresponding `docs/reqs/**/*.yml` and the formal docs (`docs/fad.md`, `docs/icd.md`,
`docs/scd.md`, `docs/sdd.md`, `docs/rtm.csv`) need updating too; this project's own doc revision
notes show stale docs (claims that don't match the implementation) are treated as real defects,
not just prose to leave alone. `tests_integration/test_tst0NN_*.py` files map 1:1 to automated
`TST-0NN` items.
