# hestIA

An on-premises enterprise AI assistant for secure, traceable querying of internal policy and compliance documentation. hestIA grounds every response in source documents that users can inspect directly, making it auditable by design.

## Features

- **Retrieval-Augmented Generation (RAG)** — hybrid dense + sparse vector search over a managed document corpus
- **Cited responses** — LLM outputs reference specific passages; users can inspect the source text inline
- **Multi-tenant access control** — role-based permissions and document classification levels enforced at query time
- **Streaming chat** — real-time token streaming via Server-Sent Events
- **Document ingestion** — upload PDF, DOCX, and XLSX files; parse, chunk, embed, and index automatically
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

## Prerequisites

- Docker and Docker Compose
- A running **vLLM** or **Ollama** inference server (for the generation model)
- A running **Qdrant** instance (vector database)
- An embedding model endpoint (vLLM or Ollama)

## Quick Start

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd A1_Prototypes

# 2. Copy the example environment file and fill in your values
cp .env.example .env   # or edit docker-compose.yml directly

# 3. Start both services
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend (UI) | http://localhost:7860 |
| Backend (API) | http://localhost:5555 |

## Configuration

All backend configuration is injected via environment variables. The defaults in `docker-compose.yml` point to a local LAN inference stack; override them to match your setup.

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5555` | Backend listening port |
| `LLM_URL` | `http://192.168.0.34:8000` | Generation model endpoint (vLLM / Ollama) |
| `EMB_URL` | `http://192.168.0.34:8001` | Embedding model endpoint |
| `RRK_URL` | _(empty)_ | Reranker endpoint (optional) |
| `DB_URL` | `http://192.168.0.34:6333` | Qdrant URL |
| `DEFAULT_GEN_MODEL` | `RedHatAI/Qwen3.6-35B-A3B-NVFP4` | Model ID for generation |
| `DEFAULT_EMB_MODEL` | `qwen3-embedding:0.6b` | Model ID for embeddings |
| `DEFAULT_RKK_MODEL` | `dengcao/Qwen3-Reranker-4B:Q8_0` | Model ID for reranking |
| `AUTH_MODE` | `local` | `local` · `ldap` · `oidc` |
| `AUTH_SECRET_KEY` | _(change this)_ | JWT signing secret |
| `AUTH_TOKEN_LIFETIME` | `360` | JWT lifetime in minutes |
| `LOG_LEVEL` | `INFO` | Python log level |

Frontend environment variables (set in `hestia-ui/` or via Docker Compose):

| Variable | Description |
|---|---|
| `PUBLIC_MICROSERVICE_URL` | Backend URL visible to the browser (SSR-side) |
| `PORT` | Frontend port (default `7860`) |

## API Overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/ready` | Readiness check (dependencies up) |
| `GET` | `/models` | List available models |
| `POST` | `/login` | Obtain JWT token |
| `POST` | `/logout` | Invalidate session |
| `GET/POST` | `/conversations/*` | Conversation CRUD |
| `POST` | `/api/chat` | Streaming RAG chat |
| `POST` | `/api/generate` | Single-turn generation |
| `POST` | `/api/search` | Direct vector search |
| `POST` | `/api/upload` | Ingest document into corpus |
| `GET/POST` | `/api/collections/*` | Collection management |
| `GET/POST` | `/admin/users` | User administration |
| `GET/POST` | `/admin/organizations` | Organization/tenant management |
| `GET/POST` | `/admin/roles` | Role management |

## Development

### Backend

```bash
cd A1_Prototypes
pip install -r requirements.txt
python -m hestia.main
```

### Frontend

```bash
cd hestia-ui
npm install
npm run dev
```

The dev server proxies API requests to `http://localhost:5555` by default (see `svelte.config.js`).

## Project Structure

```
A1_Prototypes/
├── hestia/                  # Python backend
│   ├── api/                 # FastAPI routers and schemas
│   ├── application/         # Ingestion pipeline
│   ├── config/              # Settings and environment loading
│   ├── domain/              # RAG engine, auth, access policies
│   ├── infrastructure/      # LLM, DB, parser, logging providers
│   └── templates/           # YAML workflow definitions
├── hestia-ui/               # SvelteKit frontend
│   └── src/
│       ├── lib/             # Shared components, stores, actions
│       └── routes/          # (protected)/ chat · admin · account
│                              (auth)/ login · OIDC callback
├── app/                     # Runtime data (logs, corpus index, user DB)
├── docs/                    # Architecture docs and specs
├── Dockerfile               # Backend container
└── docker-compose.yml       # Multi-service orchestration
```
