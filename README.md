# hestIA

**Status: Alpha** — this is a pre-release preview. See [Known Limitations](#known-limitations--alpha-status) before using it with real data.

hestIA is an on-premises RAG assistant for querying internal policy, compliance, and
knowledge-base documents. It grounds every response in source passages that users can inspect
directly, and logs every security-relevant action to an audit trail.

Most RAG tools assume either one shared corpus everyone can query, or a separate deployment
per team. hestIA instead treats **tenants** — departments, teams, or business units within one
organization — as first-class citizens: each tenant owns its own document collections, each
user's access within a tenant is capped by a classification level, and collections stay
isolated between tenants unless a tenant moderator explicitly requests — and another tenant's
moderator explicitly grants — cross-tenant access. One deployment can serve an entire
multi-department organization without flattening everyone into a single corpus or forcing IT
to stand up separate infrastructure per department.

## Features

- **Retrieval-Augmented Generation (RAG)** — hybrid dense + sparse vector search over a managed document corpus
- **Cited responses** — LLM outputs reference specific passages; users can inspect the source text inline
- **Tenant-scoped access with cross-tenant sharing** — document collections belong to a tenant; each user's access is capped by a classification level scoped to that tenant; tenants can request and grant each other read access to specific collections through an audited approval workflow
- **Streaming chat** — real-time token streaming via Server-Sent Events
- **Document ingestion** — upload PDF, Word, Excel, PowerPoint, Markdown, CSV/JSON, or plain text; parse, chunk, embed, and index automatically
- **Composable workflows** — RAG pipelines are YAML-defined DAGs; no code changes needed to add new retrieval strategies
- **Enterprise auth** — local, LDAP, and OIDC authentication modes
- **Audit logging** — structured JSON logs with per-request correlation IDs

## Architecture

```
hestia-ui  (SvelteKit/TypeScript)   →   REST + SSE 
hestia     (FastAPI/Python)
  ├── api/          HTTP routers, schemas, JWT security
  ├── application/  Document ingestion pipeline
  ├── domain/       RAG engine, auth services, access policies
  └── infrastructure/
        ├── llm/    vLLM · Ollama
        ├── db/     Qdrant (vectors) · SQLite (users & conversations)
        ├── parsers/ PDF · DOCX · XLSX
        └── logging/ audit trail · correlation middleware
```

Workflows are resolved from `hestia/templates/workflows/` at request time:

| Workflow | Description |
|---|---|
| `chat.yaml` | Multi-turn conversational LLM (no retrieval) |
| `generate.yaml` | Single-turn LLM generation |
| `rag_chat.yaml` | Retrieval-augmented conversational chat |
| `rag_generate.yaml` | Retrieval-augmented single-turn generation |

## External dependencies

`docker-compose.yml` in this repo only builds and runs the **`backend`** and **`frontend`**
containers — it does not provision any of the systems hestIA talks to. Before starting hestIA,
you need:

1. **An LLM serving endpoint** — either:
   - **vLLM**, serving an OpenAI-compatible API (`/v1/chat/completions`, `/v1/embeddings`, …), or
   - **Ollama**, serving its native API.

   hestIA needs at least one model that can *generate* text, and (for RAG search/ingestion to
   work) one model that can produce *embeddings*. Most chat models cannot do both — if you're
   using Ollama, pull a chat model and a dedicated embedding model separately.
2. **Qdrant** — the only supported vector database backend.
3. *(Optional)* An **LDAP** or **OIDC** identity provider, if you don't want to use hestIA's
   built-in local username/password auth.

### Fastest way to get these running for evaluation

Not a production setup — just enough to try hestIA locally. Run these as plain Docker
containers on the same machine that will run `docker compose up` for hestIA itself:

```bash
# Vector database
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# LLM server (Ollama) -- pull a chat model and a dedicated embedding model
docker run -d --name ollama -p 11434:11434 ollama/ollama
docker exec ollama ollama pull llama3.1:8b
docker exec ollama ollama pull nomic-embed-text
```

Because the hestIA `backend` container runs in its own Docker network
(`docker-compose.yml`'s `app_network`), `localhost` inside that container refers to the
container itself, **not** your host machine. Point the backend at these containers using
`host.docker.internal` (works out of the box with Docker Desktop on Windows/macOS; on Linux,
add `extra_hosts: ["host.docker.internal:host-gateway"]` to the `backend` service in
`docker-compose.yml`):

```
LLM_URL=http://host.docker.internal:11434
LLM_BACKEND=ollama
DB_URL=http://host.docker.internal:6333
DEFAULT_GEN_MODEL=llama3.1:8b
DEFAULT_EMB_MODEL=nomic-embed-text
```

## Quick Start (Docker Compose)

Prerequisites: Docker and Docker Compose, plus the external dependencies above already
running and reachable.

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd hestIA

# 2. Create a .env file with the variables docker-compose.yml expects
```

```bash
# .env
LLM_URL=http://host.docker.internal:11434
LLM_BACKEND=ollama
DB_URL=http://host.docker.internal:6333
DEFAULT_GEN_MODEL=llama3.1:8b
DEFAULT_EMB_MODEL=nomic-embed-text

# Generate a real secret, e.g.: openssl rand -hex 32
AUTH_SECRET_KEY=<32+ character random string>

# Bootstrap admin account -- created once, on first boot, if the user DB is empty
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=<a strong password>
DEFAULT_ADMIN_EMAIL=admin@example.com
```

```bash
# 3. Start both services
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend (UI) | http://localhost:7860 |
| Backend (API) | http://localhost:5555 |

Log in with the bootstrap admin credentials — you'll be required to change the password on
first login.

## Configuration

Environment variables are read once at startup (`Settings.load()`). For **auth settings, LLM
connections (generation/embedding/reranking), the vector DB connection, and notification
settings**, the env vars below only *seed* the database the first time it's empty — after
that, changing them requires editing them through the Admin Settings UI, not editing `.env`
and restarting (see [API Overview](#api-overview) for the relevant `/admin/*` endpoints). Env
vars remain authoritative for everything else: data/log paths, the bootstrap admin account,
timeouts, and token budgets.

### Backend

**Server**

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5555` | Listening port |
| `HESTIA_DATA_DIR` | `app/data` | Where the SQLite DB, corpus stats, and templates live |
| `LOG_DIR` | `logs` (sibling of `HESTIA_DATA_DIR`) | Log file directory |
| `LOG_LEVEL` | `INFO` | Python log level |
| `LOG_TO_CONSOLE` | `true` | Also emit logs to stdout |
| `MAX_CONTEXT_TOKENS` | `32000` | Context budget per request |
| `SUMMARY_TARGET_TOKENS` | `6000` | Must be less than `MAX_CONTEXT_TOKENS` |
| `SUMMARY_MODEL` | _(falls back to `DEFAULT_GEN_MODEL`)_ | Model used for conversation summarization |

**LLM provider**

| Variable | Default | Description |
|---|---|---|
| `LLM_BACKEND` | `vllm` | `vllm` or `ollama` |
| `LLM_URL` | `localhost:8000` | Generation endpoint |
| `LLM_API_KEY` | _(none)_ | Bearer token for the LLM endpoint, if required |
| `DEFAULT_GEN_MODEL` | _(none — must be set)_ | Model ID for generation/chat |
| `EMB_URL` | _(falls back to `LLM_URL`)_ | Embedding endpoint, if different from generation |
| `DEFAULT_EMB_MODEL` | _(falls back to `DEFAULT_GEN_MODEL`)_ | Model ID for embeddings |
| `RRK_URL` | _(falls back to `LLM_URL`)_ | Reranker endpoint, if different (optional) |
| `DEFAULT_RKK_MODEL` | _(falls back to `DEFAULT_GEN_MODEL`)_ | Model ID for reranking (optional) |

**Vector database**

| Variable | Default | Description |
|---|---|---|
| `DB_BACKEND` | `qdrant` | Only `qdrant` is currently supported |
| `DB_URL` | `http://localhost:6333` | Qdrant URL |
| `DB_API_KEY` | _(none)_ | Qdrant API key, if required |

**Bootstrap admin** (used once, only if the user database is empty)

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_ADMIN_USERNAME` | _(none)_ | Required together with the two below, or startup fails |
| `DEFAULT_ADMIN_PASSWORD` | _(none)_ | |
| `DEFAULT_ADMIN_EMAIL` | _(none)_ | |
| `DEFAULT_ADMIN_FIRST_NAME` | `Admin` | |
| `DEFAULT_ADMIN_LAST_NAME` | `User` | |

**Auth / JWT / rate limiting**

| Variable | Default | Description |
|---|---|---|
| `AUTH_MODE` | `local` | `local` · `ldap` · `oidc` |
| `AUTH_SECRET_KEY` | _(none — must be ≥32 characters)_ | JWT signing secret; startup fails without one long enough |
| `AUTH_ENCODING_ALGORITHM` | `HS256` | JWT signing algorithm |
| `AUTH_TOKEN_LIFETIME` | `60` | JWT lifetime, minutes |
| `AUTH_PW_LENGTH` | `15` | Minimum local password length |
| `AUTH_MAX_ATTEMPTS` | `5` | Failed logins before lockout (keyed by username, not IP) |
| `AUTH_LOCKOUT_DURATION` | `5` | Lockout duration, minutes |
| `AUTH_IP_RATE_LIMIT_ATTEMPTS` | `30` | Login attempts per IP window |
| `AUTH_IP_RATE_LIMIT_WINDOW_MINUTES` | `1` | Window for the above |
| `AUTH_AUDIT_LOGS` | `false` | Emit `auth_attempt` audit events (off by default) |
| `LDAP_GROUP_MAPPING` | _(none)_ | JSON, e.g. `{"cn=admins,...": ["admin"]}` — parsed regardless of `AUTH_MODE`, but only meaningful under `ldap` |

**LDAP** (only read when `AUTH_MODE=ldap`)

| Variable | Default | Description |
|---|---|---|
| `LDAP_HOST` | _(none)_ | |
| `LDAP_PORT` | `636` | |
| `LDAP_USE_SSL` | `true` | |
| `LDAP_VALIDATE_CERT` | `true` | |
| `LDAP_SEARCH_BASE` | _(none)_ | |
| `LDAP_USER_ATTRIBUTE` | `uid` | |
| `LDAP_MAIL_ATTRIBUTE` | `mail` | |
| `LDAP_USER_DN_TEMPLATE` | _(none)_ | |
| `LDAP_APP_DN` / `LDAP_APP_PASSWORD` | _(none)_ | Service account for directory search |
| `LDAP_GROUP_FILTER` | _(none)_ | |
| `LDAP_MODE` | `auto` | |

**OIDC** (only read when `AUTH_MODE=oidc`)

| Variable | Default | Description |
|---|---|---|
| `OIDC_PROVIDER_URL` | _(none)_ | |
| `OIDC_CLIENT_ID` | _(none)_ | |
| `OIDC_CLIENT_SECRET` | _(none)_ | |
| `OIDC_SCOPES` | `openid,profile,email` | |
| `OIDC_ROLE_CLAIM` | `roles` | |
| `OIDC_ROLE_MAPPING` | _(none)_ | JSON, claim value → hestIA role |
| `OIDC_ORG_CLAIM` | `organization` | |
| `OIDC_ORG_MAPPING` | _(none)_ | JSON, claim value → hestIA org |
| `OIDC_REDIRECT_ALLOWLIST` | _(none)_ | Comma-separated list |

### Frontend

| Variable | Default | Description |
|---|---|---|
| `PRIVATE_MICROSERVICE_URL` | `http://localhost:5555` | Backend URL, server-side only — never sent to the browser |
| `PRIVATE_HELP_DATA_DIR` | `./data/manual` | Where in-app help content is read from |
| `PUBLIC_AUTH_MODE` | _(none)_ | Must match the backend's `AUTH_MODE`; controls the login page |
| `PORT` | `3000` (adapter default) | Frontend listening port — `docker-compose.yml` overrides this to `7860` |

## Running locally without Docker

For development against the code directly, without containers.

### Backend

Requires Python 3.13 and the `pandoc` system package (used for DOCX parsing).

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

The backend does **not** load `.env` files automatically — there's no `python-dotenv`
dependency — so export your configuration into the shell session before starting it:

```bash
# bash
python -m hestia.main

```

The server runs without `--reload`; restart it after any code change.

### Frontend

Requires Node 22.

```bash
cd hestia-ui
npm install
npm run dev
```

`hestia-ui/.env` is already checked in with working defaults for local development
(`PRIVATE_MICROSERVICE_URL=http://localhost:5555`), so the dev server (default port `5173`)
will proxy to a backend started as above without further setup.


## API Overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check (unauthenticated) |
| `GET` | `/ready` | Readiness check (unauthenticated) |
| `GET` | `/models` | List available models (unauthenticated) |
| `POST` | `/login` | Obtain JWT token |
| `POST` | `/logout` | Invalidate session |
| `GET` | `/account` | Current user profile |
| `GET/POST` | `/conversations/*` | Conversation CRUD |
| `POST` | `/api/chat` | Streaming RAG chat |
| `POST` | `/api/generate` | Single-turn generation |
| `POST` | `/api/search` | Direct vector search |
| `POST` | `/api/upload` | Ingest a document into the corpus |
| `GET/POST` | `/api/collections/*` | Collection management |
| `GET/POST` | `/admin/users/*` | User administration |
| `GET/POST` | `/admin/organizations/*` | Organization/tenant management |
| `GET` | `/admin/roles` | Role listing |
| `GET/POST/PUT` | `/admin/llm/connections`, `/admin/auth/settings`, `/admin/workflows`, `/admin/logs` | Runtime admin configuration — see [Configuration](#configuration) |

Routes for `/api/chat`, `/api/generate`, `/api/search`, and `/api/upload`/`/api/collections`
are only mounted if a matching LLM/vector-DB connection is configured (env-seeded or added via
the admin API) — an unconfigured route 404s rather than erroring.

## Known Limitations / Alpha Status

This is an early, pre-production release. Known, documented gaps (see `docs/sdd.md` §12.2
for the full list):

- **No backup/restore mechanism** for the SQLite user database or Qdrant collections. The
  Docker volume mounts survive container restarts, but that is not a backup strategy.
- **Secrets are stored in plaintext** in SQLite — LLM/vector-DB API keys and LDAP/OIDC client
  secrets are not encrypted at rest.
- **No TLS or internal transport encryption is bundled.** Put a reverse proxy in front of
  hestIA for anything beyond local evaluation, and secure the network path to your LLM/Qdrant
  endpoints separately.
- **The frontend container runs as root** (the backend container drops to a non-root user).
- **Single-node only** — no clustering, HA, or horizontal scaling topology is implemented.

## Documentation

- [`docs/manual/README.md`](docs/manual/README.md) — end-user guide (login, chat, documents, administration)
- [`docs/sdd.md`](docs/sdd.md) — software design document (architecture, deployment, risk findings)
- [`docs/icd.md`](docs/icd.md) — interface control document (external system integrations)
- [`docs/reqs/`](docs/reqs/) — Doorstop-managed requirements/test traceability tree (`MRS` → `SRS` → `TST` → `TRP`)

## Project Structure

```
A1_Prototypes/
├── hestia/                  # Python backend
│   ├── api/                 # FastAPI routers and schemas
│   ├── application/         # Ingestion pipeline
│   ├── config/               # Settings and environment loading
│   ├── domain/               # RAG engine, auth, access policies
│   ├── infrastructure/       # LLM, DB, parser, logging providers
│   └── templates/             # YAML workflow definitions
├── hestia-ui/                 # SvelteKit frontend
│   └── src/
│       ├── lib/                # Shared components, stores, actions
│       └── routes/             # (protected)/ chat · admin · account
│                                  (auth)/ login · OIDC callback
├── app/                       # Runtime data (logs, corpus index, user DB)
├── docs/                      # Architecture docs and specs
├── Dockerfile                  # Backend container
└── docker-compose.yml          # Multi-service orchestration
```

## Changelog v0.3

**Added**

- Admin-configurable runtime settings: LLM/embedding/vector-DB connections, auth and logging
  settings with log export, and a visual editor for the RAG workflow pipeline — all
  configurable from the Admin UI without a restart.
- Tenant collaboration workflows: users can request to join a tenant, moderators can invite
  users directly, and moderators can request and grant cross-tenant access to specific
  collections, with admin broadcast notifications.
- Automatic chunking-strategy detection (block/section, prose vs. table) with manual override,
  plus per-document metadata inspection and editing after upload.
- Collection ownership can now be reassigned between organisations by an admin.
- Per-conversation knowledge-base/corpus selection, with keyboard shortcuts to switch between
  corpora.
- The bootstrap admin account is now configured via `DEFAULT_ADMIN_USERNAME`/`PASSWORD`/`EMAIL`
  environment variables on first boot, instead of a hardcoded default.

**Fixed**

- Classification level mismatch between backend and frontend enums, which could show or hide
  the wrong documents.
- Chat used a hardcoded model name that caused errors once the underlying model changed; the
  active model is now read from settings.
- First boot could fail to initialize because the `app/data` directory wasn't created if
  missing.
- Retrieved RAG context was being resent on every turn of a conversation, needlessly bloating
  the context window; it's now sent only with the originating query.
- Audit logging could report a partially-successful admin action as a failure; account
  expiration used mismatched time units that could lock accounts out immediately; streaming
  chat/generate could crash if a save-conversation flag was omitted from the request;
  non-streaming responses were mislabeled as JSON while actually returning raw text.
