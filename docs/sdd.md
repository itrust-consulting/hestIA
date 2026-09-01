# System Design Document (SDD)

Service: hestIA  
Version: alpha_v0.3  
Classification: INTERNAL  
Date: 2026-06-15

---

## 1 Introduction

### 1.1 Context

This document describes the internal design and implementation of hestIA, an on-premises AI assistance platform developed by iTrust Luxembourg for IT governance and compliance use cases. hestIA is defined at the functional level by the Functional Architecture Document (FAD), at the conceptual level by the System Concept Document (SCD), and at the interface level by the Interface Control Document (ICD). Those documents govern *what* the system does and how it presents itself externally; this document governs *how* it is built.

### 1.2 Objectives

This System Design Document specifies the internal implementation of hestIA: the module and service structure, data models, persistence strategy, workflow execution engine, external integrations, security controls, logging infrastructure, and deployment configuration. It serves as the primary reference for engineering onboarding, architecture review, and certification or audit of the as-built system.

### 1.3 Document Scope

**Covered by this document:**
- Internal module and layered architecture
- Service instantiation and dependency wiring
- Data models and SQLite schema
- Workflow execution graph and runner design
- Integration design for LLM, vector database, and identity providers
- JWT authentication and policy enforcement implementation
- Logging and audit infrastructure
- Containerisation and deployment configuration

**Not covered by this document:**
- Functional requirements (→ FAD)
- External API contract and endpoint specifications (→ ICD)
- System rationale and operational context (→ SCD)

---

## 2 System Overview

### 2.1 Architecture Summary

hestIA is a two-tier, two-container system composed of a Python backend and a TypeScript/SvelteKit frontend, communicating over an internal Docker bridge network.

The **backend** (`hestia/`) is a FastAPI application that owns all business logic, data persistence, and external service integrations. It exposes a REST API consumed by the frontend and, optionally, by direct API clients. It runs on port 5555 and is the sole point of access to the SQLite user database, the Qdrant vector store, and the LLM inference backend.

The **frontend** (`hestia-ui/`) is a SvelteKit application that runs on port 7860. It acts as a server-rendered proxy layer: SvelteKit server-side routes relay API requests from the browser to the backend, attaching the session JWT from an HTTP-only cookie. The browser-side Svelte application handles interactive state (chat streaming, uploads, admin forms) via client-side API calls that route through the SvelteKit server's `/api/` namespace.

External infrastructure (LLM inference server, Qdrant, LDAP/OIDC provider) is assumed to be pre-deployed and reachable on the network. hestIA does not bundle or manage these services.

### 2.2 Design Approach

The backend follows a **layered architecture** with four distinct layers:

1. **API layer** — FastAPI routers, request validation, dependency injection, rate limiting, middleware.
2. **Domain layer** — Business logic: authentication, policy enforcement, RAG orchestration, workflow graph definition.
3. **Application layer** — Coordination across domain services for multi-step operations (ingestion pipeline).
4. **Infrastructure layer** — Concrete implementations of external I/O: SQLite repository, Qdrant client wrapper, LLM provider adapters, file parsers, logging.

Service wiring is performed at startup by a manual **dependency injection container** (`hestia/container.py`). The container is attached to application state and retrieved per-request through FastAPI's dependency mechanism. This design avoids global state and enables selective service activation via the `services_to_start` configuration list.

Workflow execution uses a **graph-based orchestration model** where execution plans are constructed at request time from YAML templates and executed node-by-node by a synchronous runner. This enables composition of multi-step RAG pipelines without code changes.

---

## 3 Component Design

The functional components defined in the FAD (FC-xx) are implemented through the components described here.

### 3.1 System Components

| Component | Description |
|---|---|
| FastAPI application | Entry point; configures middleware, routers, and lifespan |
| Dependency injection container | Wires and holds all service and provider instances |
| Request handler | Resolves execution requests: policy check, plan build, runner dispatch |
| Authentication service | Credential verification across local, LDAP, and OIDC modes |
| User service | User lifecycle, password management, role and org management |
| Policy enforcement | Collection-level access control and classification filtering |
| Workflow engine | YAML template loading, execution graph construction, node runner |
| Ingestion pipeline | Multi-format document parsing, chunking, encoding, and upsert |
| Dense encoder | Text-to-vector embedding via the configured LLM provider |
| Sparse encoder | BM25 TF-IDF tokenisation and corpus management (in-process) |
| Retriever | Hybrid dense+sparse query execution against Qdrant |
| Generator | LLM completion and chat generation (streaming and batch) |
| User repository | SQLite CRUD for users, roles, organisations, conversations, messages |
| Qdrant adapter | Qdrant collection management, upsert, and search |
| LLM provider adapters | HTTP clients for vLLM and Ollama (generation, chat, embed) |
| Document parsers | Format-specific extractors (PDF, DOCX, XLSX, PPTX, MD, CSV, JSON, TXT) |
| Logging infrastructure | JSON-structured async logging; separate system and audit streams |
| SvelteKit frontend | Server-rendered UI with BFF proxy for backend API calls |

### 3.2 Component Breakdown

#### FastAPI Application (`hestia/main.py`)

- **Responsibilities**: Construct and configure the FastAPI instance; register middleware and exception handlers; orchestrate startup (settings load → container build → router registration) and shutdown.
- **Key modules**: `hestia/main.py`, `hestia/api/routers/registry.py`, `hestia/api/limiter.py`, `hestia/api/error_handlers.py`
- **Middlewares**: Correlation middleware (request ID propagation and HTTP access logging), rate-limiting middleware.
- **Dependencies**: Settings, Container, Request Handler

#### Dependency Injection Container (`hestia/container.py`)

- **Responsibilities**: Read settings; instantiate LLM provider, Qdrant client, and all domain services in a defined order; validate mutual dependencies (e.g., the ingestion service requires both encoder services to be enabled).
- **Key modules**: `hestia/container.py`
- **Design**: The container holds two registries: `providers` (infrastructure clients: LLM, vector DB) and `services` (domain services: auth, users, dense encoder, sparse encoder, generator, retriever, ingestion). Services are only instantiated if their name appears in `services_to_start`.
- **Dependencies**: All domain and infrastructure modules

#### Request Handler (`hestia/handler.py`)

- **Responsibilities**: Serve as the execution façade for all AI workflows; apply policy; build an execution graph from a YAML template; dispatch to the workflow runner; emit audit log entries.
- **Key modules**: `hestia/handler.py`
- **Design**: Maps four execution types (`generate`, `rag_generate`, `chat`, `rag_chat`) to corresponding YAML workflow templates. For chat requests with persistence enabled, wraps the runner with a persistence layer that writes conversation turns to SQLite after generation completes.
- **Dependencies**: Container, Policy enforcement, Workflow engine

#### Authentication Service (`hestia/domain/auth/`)

- **Responsibilities**: Verify credentials across three modes (local, LDAP, OIDC); auto-provision LDAP and OIDC users on first login; map external group/role claims to internal roles.
- **Key modules**: `hestia/domain/auth/service.py`, `hestia/domain/auth/users.py`, `hestia/domain/auth/oidc.py`
- **LDAP mode**: Binds to the directory server, searches for the user, and verifies the password. On success, creates a local shadow account if one does not exist, mapping directory groups to local roles via a configurable mapping.
- **OIDC mode**: Exchanges an authorization code for tokens via the provider's token endpoint, fetches user info, and auto-provisions a local account on first login.
- **Dependencies**: User service, LDAP service, OIDC service, Audit logger

#### Policy Enforcement (`hestia/domain/policies/`)

- **Responsibilities**: Enforce access control on every AI execution request before the workflow runner is invoked.
- **Key modules**: `hestia/domain/policies/guard.py`
- **Design**: An ordered chain of policy evaluators is applied to each request. The current implementation contains one policy — collection access — which evaluates the user's permitted collections and returns one of three decisions: `ALLOW`, `DENY`, or `FILTER` (with a classification ceiling injected into the query options).
- **Dependencies**: User permissions model, Audit logger

#### Workflow Engine (`hestia/domain/rag/`, `hestia/handler.py`)

- **Responsibilities**: Load YAML workflow templates, hydrate them with request context, instantiate an execution graph, and execute nodes in topological order.
- **Key modules**: `hestia/domain/rag/graph.py`, `hestia/domain/rag/templater.py`, `hestia/handler.py`
- **Template system**: Workflow YAML files reference reusable node fragments. Context variables from the execution request are substituted into the template before the graph is instantiated. Inter-node data references are resolved at runtime from a slot dictionary passed between nodes.
- **Node types supported**: `EncodeDense`, `EncodeSparse`, `Retrieve`, `Augment`, `Generate`, `Chat`
- **Dependencies**: Container services, YAML templates under `hestia/templates/`

#### Ingestion Pipeline (`hestia/application/ingestion.py`)

- **Responsibilities**: Accept a document file path and collection target; parse the file; split into sections; generate dense and sparse embedding vectors; upsert into Qdrant.
- **Key modules**: `hestia/application/ingestion.py`
- **Processing flow**: Format-specific parser → Markdown extraction → section chunking → dense batch embedding → sparse BM25 encoding with corpus update → Qdrant collection initialisation → batched point upsert.
- **Supported formats**: PDF, DOCX, XLSX/XLSM, PPTX, JSON, CSV, TXT, Markdown
- **Dependencies**: Dense encoder, Sparse encoder, Qdrant adapter, Parser implementations

#### User Repository (`hestia/infrastructure/db/`)

- **Responsibilities**: All SQLite reads and writes for the user database: users, roles, organisations, memberships, tenant–collection grants, conversations, and messages.
- **Key modules**: `hestia/infrastructure/db/user_repository.py`
- **Design**: Per-thread connections are used for reads. All mutations are executed inside explicit transactions protected by a serialising write lock, ensuring safe concurrent access without connection pooling.
- **Dependencies**: SQLite (Python standard library)

#### SvelteKit Frontend (`hestia-ui/`)

- **Responsibilities**: Render the user interface; proxy API calls server-side to the backend with session JWT attachment; enforce route-level access guards.
- **Key modules**: `src/hooks.server.ts` (session hydration and route guard), `src/lib/server/backend.ts` (backend proxy), `src/lib/api/client.ts` (browser-side API client), `src/lib/stores/` (reactive state for chat, conversations, uploads)
- **Route structure**: Protected routes under `/(protected)/` covering chat, admin, account, and help; public login route.
- **Design**: All calls to the backend originate from SvelteKit server-side API routes (`src/routes/api/**`), which are the sole consumers of `PRIVATE_MICROSERVICE_URL`. Browser code calls only relative paths on the SvelteKit server.
- **Dependencies**: SvelteKit, backend API

### 3.3 Layered Structure

```
┌──────────────────────────────────────────────┐
│  API Layer (hestia/api/)                     │
│  Routers · Schemas · Dependencies · Security │
│  Rate limiter · Error handlers · Middleware  │
├──────────────────────────────────────────────┤
│  Domain Layer (hestia/domain/)               │
│  Auth · Policy · RAG graph · Templater       │
│  Workflow runner · Citation formatter        │
├──────────────────────────────────────────────┤
│  Application Layer (hestia/application/)     │
│  Ingestion pipeline coordinator              │
├──────────────────────────────────────────────┤
│  Infrastructure Layer (hestia/infrastructure/)│
│  SQLite repo · Qdrant adapter · LLM clients  │
│  File parsers · Logging · HTTP client        │
└──────────────────────────────────────────────┘
```

Dependency direction is strictly top-down. Domain logic does not import from the API layer; infrastructure modules do not import from domain or application layers. Cross-layer access is mediated through protocol interfaces (`DBProvider`, `LLMProvider`, `BaseParser`).

---

## 4 Data Design

### 4.1 Data Models

#### Relational store (SQLite — `users.db`)

| Entity | Description | Key Fields |
|---|---|---|
| `users` | System user accounts | identity, credentials (hash + salt), auth source, expiry |
| `roles` | System roles (admin, user) | name, description |
| `user_roles` | Role assignment with validity window | user, role, start/expiry timestamps |
| `organizations` | Tenant organisations | name, abbreviation |
| `user_orgs` | User–organisation membership with per-tenant classification clearance and role | user, org, classification level, tenant role |
| `tenant_collections` | Collection grants to organisations | org, collection, role (owner/access), classification ceiling |
| `conversations` | Named chat conversation threads per user | owner, title, timestamps |
| `messages` | Individual turns within a conversation | conversation, role (user/assistant/system), content, metadata (citations, chain-of-thought), model options |

#### Vector store (Qdrant — per collection)

Each Qdrant collection stores one point per document chunk. Points carry:
- A **dense** named vector (cosine similarity, dimension determined by the embedding model).
- A **sparse** named vector (BM25 TF-IDF indices and values).
- A **payload** with document content, source identifiers, section metadata, document-level metadata (title, author, tenant, document ID), classification level, upload provenance, and adjacency links to the previous and next chunk.

Payload indexes are maintained on the document identifier and classification level fields to support filtered retrieval.

#### In-memory domain models

| Model | Description |
|---|---|
| `User` | Authenticated user context passed through the request lifecycle; includes identity, roles, org memberships, and derived permissions |
| `Permissions` | Derived access rights: admin flag, per-collection access grants, moderated and role-assignable tenant lists |
| `ExecutionRequest` | Input to the workflow engine: user context, execution type, conversation history, prompt, model selection, collection, persistence flags |
| `ExecutionGraph` | Runtime execution plan: ordered list of nodes, directed edges, entrypoint, exitpoints |
| `Node` | Single workflow step: type, wired inputs/outputs, model override, generation options |

### 4.2 Persistence Design

**User database**: SQLite with WAL journal mode and foreign key enforcement. Write transactions are serialised by an application-level lock. Connections are per-thread and reused for their lifetime. Schema is initialised and migrated incrementally on startup. There is no ORM; all queries use raw SQL with positional parameters.

**Vector database**: Qdrant is accessed over HTTP via the official Python SDK. Collections are created lazily on first ingest. Upsert operations are batched (64 points per request). The HNSW index is created with parameters suited to high-recall approximate nearest-neighbour search. Sparse vectors use an in-memory index.

**Sparse corpus statistics**: BM25 vocabulary and document-frequency tables are persisted as JSON files under `app/data/corpus_dir/`, one file per Qdrant collection. All files are loaded into an in-process cache at startup. Updates are written to disk under a write lock before the in-memory cache is refreshed.

**Conversation persistence**: Conversations and messages are written to SQLite by the request handler after generation completes. For streaming responses, the full response is buffered in memory and persisted once the stream closes.

---

## 5 Interface Implementation

### 5.1 API Structure

Backend endpoints are organised as FastAPI router modules registered through a central router registry (`hestia/api/routers/registry.py`). Each router is associated with a URL prefix, tag group, and an optional service dependency. Routers that depend on an inactive service are not mounted; core routers (health, auth, account, conversations, admin, help) are always registered.

| Router group | Prefix | Always on | Service gate |
|---|---|---|---|
| health | — | Yes | — |
| auth | — | Yes | — |
| account | — | Yes | — |
| conversations | — | Yes | — |
| admin | `/admin` | Yes | — |
| help | — | Yes | — |
| encode | `/api` | No | dense encoder |
| generate | `/api` | No | generator |
| chat | `/api` | No | generator |
| search | `/api` | No | retriever |
| ingestion | `/api` | No | ingestion pipeline |

The container and request handler are stored on application state at startup and injected into route handlers through FastAPI's dependency mechanism. The authenticated user object is resolved per-request by decoding the JWT and loading the full user profile from the user service.

Rate limiting is applied to the login endpoint via a configurable per-IP request limit derived from the authentication settings.

### 5.2 Request Processing Flow

**Standard AI request (non-streaming):**

An authenticated request arrives at the chat or generate router. The router resolves the current user from the JWT, constructs an execution request from the validated request body, and passes it to the request handler. The handler applies the policy chain (returning an error on denial or injecting query filters on restricted access), selects the appropriate YAML workflow template, builds an execution graph, and runs the graph node-by-node. Each node delegates to the corresponding domain service (encoder, retriever, generator). The final response is returned as JSON.

**Streaming AI request:**

The flow is identical through the policy and graph-building stages. The final generation node is invoked in streaming mode, and the router returns a streaming response. The response wrapper buffers output, segregates chain-of-thought tokens from content tokens, and emits a closing envelope containing conversation identifiers and the citation list once the stream ends.

**Ingestion request:**

An admin or authorised user uploads a file via multipart form. The ingestion router saves the file temporarily and dispatches an ingestion request to the pipeline. The pipeline selects a parser by file extension, extracts Markdown content and metadata, splits the content into sections, computes dense and sparse embedding vectors, initialises the target collection if needed, and upserts all points. The result (chunk count, elapsed time) is returned as JSON.

---

## 6 External Integrations

### 6.1 LLM Provider

The LLM backend is abstracted behind a provider protocol (`hestia/infrastructure/llm/protocol.py`) with three operations: generation, chat, and embedding. Two adapters are implemented:

- **vLLM adapter** (`hestia/infrastructure/llm/vllm.py`): Targets an OpenAI-compatible HTTP endpoint. Separate base URLs can be configured for generation/chat, embeddings, and reranking. Streaming is handled via server-sent events.
- **Ollama adapter** (`hestia/infrastructure/llm/ollama.py`): Targets an Ollama instance via its native HTTP API. Streaming is handled via chunked transfer encoding.

The same provider instance is shared between the generator and dense encoder services. The active adapter is selected at startup from the `LLM_BACKEND` configuration variable.

### 6.2 Vector Database

The Qdrant adapter (`hestia/infrastructure/db/qdrant.py`) implements the `DBProvider` protocol using the official `qdrant-client` SDK.

- **Ingestion**: Collections are created on first use with named dense and sparse vector configurations. Points are written in batches.
- **Retrieval**: Queries are executed as dense-only, sparse-only, or hybrid (dense + sparse with rank fusion), depending on which vectors are present. Classification-level filtering is applied as a payload filter when the policy engine constrains the request.
- **Administration**: Collection listing, deletion, and per-document point deletion (filtered by document identifier) are supported for administrative operations.

### 6.3 Identity Provider

**LDAP** (`hestia/domain/auth/users.py`): Connects to an LDAP or Active Directory server using the `ldap3` library, with configurable SSL and certificate validation. Authentication uses a service-account bind followed by a user search and credential verification. Group membership is retrieved from the directory and mapped to internal roles via a configurable mapping table. First-time LDAP users are auto-provisioned as local accounts.

**OIDC** (`hestia/domain/auth/oidc.py`): Implements the Authorization Code flow against a configurable OIDC provider. After code exchange, user identity and role/organisation claims are extracted from the provider's user-info response using configurable claim names. Role and organisation mappings translate provider-specific values to internal equivalents. First-time OIDC users are auto-provisioned as local accounts.

### 6.4 External Storage

No external object storage is used. Uploaded documents are written to a temporary path during ingestion and deleted once the pipeline completes. The sparse corpus statistics files and the SQLite database are stored under the `app/data/` directory, which is bind-mounted as a Docker volume to persist data across container restarts.

---

## 7 Workflow Engine Design

### 7.1 Template System

Workflow templates are stored as YAML files under `hestia/templates/`, organised in two subdirectories:

- `base/`: Reusable node fragment definitions, one per node type (`encode_dense`, `encode_sparse`, `retrieve`, `augment`, `generate`, `chat`).
- `workflows/`: Complete workflow definitions composing base fragments: `generate`, `rag_generate`, `chat`, `rag_chat`.

A workflow YAML specifies an entrypoint, a list of fragment includes, an ordered node list (each either referencing a fragment with overrides or defined inline), and an optional explicit edge list.

### 7.2 Context Interpolation

At request time, the template builder constructs a context dictionary from the execution request fields. YAML values containing `${key}` patterns are substituted with the corresponding context value. Inter-node data references, written as `?slot_name`, are left as-is in the graph and resolved at runtime from the execution slot dictionary passed between nodes.

### 7.3 Execution Model

The workflow runner traverses the execution graph in linear order (derived from the edge list, or falling back to node declaration order). Each intermediate node is executed synchronously; its outputs are written to the shared slot dictionary for use by subsequent nodes. The final node is executed in streaming or batch mode according to the request.

| Node type | Responsibility | Service used |
|---|---|---|
| `EncodeDense` | Embed query text as a dense vector | Dense encoder |
| `EncodeSparse` | Encode query text as a BM25 sparse vector | Sparse encoder |
| `Retrieve` | Query Qdrant with dense, sparse, or hybrid query | Retriever |
| `Augment` | Format retrieved chunks into a RAG prompt with citation map | In-process |
| `Generate` | Single-turn LLM completion | Generator |
| `Chat` | Multi-turn LLM chat with conversation history | Generator |

### 7.4 Augmentation and Citation

The `Augment` node formats a structured RAG prompt embedding retrieved chunk content alongside a source map that assigns each unique source document a short integer citation key. After generation, the response text is scanned for citation references; only citation keys that appear in the generated text are included in the final citation list persisted with the message.

### 7.5 Extensibility

New node types are registered in the workflow runner without modifying existing nodes. New workflow compositions are expressed as YAML template files and take effect on the next restart, requiring no code changes.

---

## 8 Security Design

### 8.1 Authentication

JWT tokens are issued on successful login. The payload contains the user UUID and expiry timestamp, signed with HMAC-SHA256 using the `AUTH_SECRET_KEY`. Token lifetime is configurable (default: 360 minutes).

On each authenticated request, the JWT is decoded, the user UUID is extracted, and the full user profile (roles, organisation memberships, derived permissions) is loaded from the user service. Token expiry and decode failures each produce an HTTP 401 response.

The SvelteKit frontend stores the JWT in an HTTP-only cookie. The server hook reads this cookie on every request, fetches the user profile from the backend, and makes it available to server-side route guards and page load functions.

### 8.2 Password Storage

Passwords for local accounts are hashed with PBKDF2-HMAC-SHA256 using a per-user random salt and 210,000 iterations. Minimum password length is enforced at account creation (default: 15 characters).

### 8.3 Authorization

**Role-based access** is enforced at the API layer. Router handlers explicitly check the resolved user's permissions (admin, tenant moderator, or collection moderator) before executing administrative operations.

**Collection-level access** is enforced at the workflow layer by the policy chain, which runs before graph execution on every AI request. The policy evaluates the user's per-collection grants derived from tenant membership and collection assignments. When access is permitted but restricted to a classification ceiling, the ceiling value is injected as a Qdrant payload filter so that only chunks at or below the permitted classification are retrieved.

### 8.4 Rate Limiting

Per-IP rate limiting is applied to the login endpoint. The limit parameters (maximum attempts and lockout window) are derived from authentication settings and configured dynamically after container build.

### 8.5 Secret Management

All secrets (JWT signing key, LLM API key, Qdrant API key, OIDC client secret, LDAP bind password) are read exclusively from environment variables at startup. No secrets are stored in code or committed configuration files. The JWT signing key is validated to be at least 32 characters at startup; the application refuses to start if this constraint is not met.

### 8.6 Frontend Security

The SvelteKit server hook appends `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` to every response. Access to admin API routes is gated server-side on the presence of admin or moderator privileges, providing a defence-in-depth layer ahead of the backend's own authorization checks.

---

## 9 Logging and Monitoring

### 9.1 Logging Architecture

Logging is initialised once at startup. All backend log output passes through a non-blocking queue handler that feeds a background listener thread, ensuring logging I/O does not block request processing.

Two file-based log streams are maintained:

| Stream | File | Rotation | Content |
|---|---|---|---|
| System | `app/logs/system.log` | Size-based: 10 MB, 5 backups | All application loggers except the audit logger |
| Audit | `app/logs/audit.log` | Time-based: daily, 90-day retention | Audit logger only |

Both streams produce structured JSON records including timestamp, log level, logger name, request correlation ID, event name, and all additional structured fields provided by the caller.

An optional console handler (enabled by default) emits human-readable output and excludes audit records.

### 9.2 Correlation ID Propagation

The correlation middleware reads the `X-Request-ID` request header or generates a UUID for each incoming request. The ID is stored in a context variable scoped to the current execution context and automatically stamped onto every log record emitted during that request, regardless of which module emits the record. The ID is also returned in the `X-Request-ID` response header.

### 9.3 Audit Logging

A typed audit logger (`hestia/infrastructure/logging/audit.py`) provides a stable interface for recording security-relevant events. Raw prompt and response content is never written to the audit log; only metadata (identifiers, lengths, timing, decisions) is recorded.

| Event | Trigger | Key fields |
|---|---|---|
| Authentication attempt | Login (success or failure) | username, success flag, auth source, failure reason |
| Policy decision | Access control evaluation on AI request | user ID, execution type, collection, decision (allow/deny/filter) |
| AI request | Start of a workflow execution | user ID, execution type, model, collection, prompt length |
| AI response | Completion of a workflow execution | user ID, execution type, response length, latency |
| Admin action | Administrative operation | actor, action name, target resource |

### 9.4 Health Endpoint

A health endpoint is always registered and does not require authentication, making it suitable for container liveness and readiness checks.

---

## 10 Deployment and Runtime

### 10.1 Deployment Model

hestIA is deployed as two Docker containers coordinated by Docker Compose:

| Service | Image source | Port | Role |
|---|---|---|---|
| `backend` | `./Dockerfile` (Python 3.13-slim) | 5555 | FastAPI application server |
| `frontend` | `./hestia-ui/Dockerfile` | 7860 | SvelteKit SSR server |

The two containers share a Docker bridge network. The frontend communicates with the backend using the internal Docker service hostname. No reverse proxy is bundled; external access is assumed to be mediated by an upstream proxy (e.g., Nginx or Traefik) that terminates TLS.

The backend image installs `pandoc` as a system dependency for document conversion, runs as a non-root user, and exposes port 5555. The `app/data/` directory is bind-mounted from the host, providing persistence for the user database, sparse corpus files, and log files across container restarts.

External services (LLM inference server, Qdrant, LDAP/OIDC provider) are not managed by the Compose file and are assumed to be reachable at the URLs specified by environment variables.

### 10.2 Configuration Management

All configuration is managed through environment variables, read at a single location during startup. There are no runtime configuration files beyond the Compose file and its `.env` substitution.

Key environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `PORT` | Backend listen port | `5555` |
| `LLM_BACKEND` | LLM adapter selection (`vllm` / `ollama`) | `vllm` |
| `LLM_URL` | LLM generation/chat endpoint | `localhost:8000` |
| `EMB_URL` | Embedding endpoint | Same as `LLM_URL` |
| `RRK_URL` | Reranking endpoint | Same as `LLM_URL` |
| `DB_URL` | Qdrant endpoint | `http://localhost:6333` |
| `LLM_API_KEY` / `DB_API_KEY` | Optional bearer tokens for LLM and Qdrant | None |
| `DEFAULT_GEN_MODEL` | Default generation model name | — |
| `DEFAULT_EMB_MODEL` | Default embedding model name | — |
| `AUTH_MODE` | Authentication mode (`local` / `ldap` / `oidc`) | `local` |
| `AUTH_SECRET_KEY` | JWT signing key (minimum 32 characters) | Required |
| `AUTH_TOKEN_LIFETIME` | Token validity in minutes | `360` |
| `AUTH_MAX_ATTEMPTS` | Login attempts before lockout | `5` |
| `AUTH_LOCKOUT_DURATION` | Lockout window in minutes | `5` |
| `LDAP_HOST` / `LDAP_PORT` / `LDAP_SEARCH_BASE` | LDAP connection parameters | — |
| `OIDC_PROVIDER_URL` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | OIDC connection parameters | — |
| `HESTIA_DATA_DIR` | Override for the data directory path | `app/data` |
| `LOG_LEVEL` | Root log level | `INFO` |
| `LOG_TO_CONSOLE` | Enable console log handler | `true` |

**Service activation**: A `services_to_start` list controls which domain services are instantiated at startup. Omitting a service name prevents the corresponding router from being mounted and its resources from being allocated. This mechanism enables deploying a backend instance configured only for, for example, search and chat without ingestion.

---

## 11 Constraints and Limitations

| Constraint | Description |
|---|---|
| SQLite write serialisation | All write transactions are serialised by an application-level lock. High-concurrency write workloads (e.g., simultaneous ingestion jobs) will queue. |
| Synchronous ingestion | Document ingestion runs synchronously within the request thread. Large documents or slow embedding models block the worker for the full duration. No background task queue is used. |
| Sparse corpus atomicity | Sparse corpus files are overwritten on each document addition or removal. A process crash during a write may leave a corrupted file; no atomic write strategy is implemented. |
| In-memory sparse corpus | All corpus vocabulary and frequency tables are held in process memory. Large collections with large vocabularies will increase memory consumption proportionally. |
| No conversation pagination in all clients | The repository supports limit/offset pagination, but not all API consumers expose pagination controls, limiting access to large conversation histories. |
| JWT revocation | Tokens cannot be revoked before expiry. Logging out deletes the browser cookie but the token remains cryptographically valid until it expires. |
| No LLM request queue | Concurrent LLM requests are forwarded directly to the provider. Provider-side capacity limits are not managed by hestIA. |
| LDAP group membership at login time | Group membership is fetched from the directory at each login and not cached. Changes to directory group membership take effect only after the user's next login. |
| Single Qdrant instance | The system is designed against a single Qdrant endpoint. No multi-node, replicated, or sharded Qdrant configuration is assumed. |
