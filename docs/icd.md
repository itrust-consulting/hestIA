# Interface Control Document (ICD)

**Service:** hestIA API
**Version:** alpha_v0.3
**Classification:** INTERNAL
**Date:** 2026-06-11
**Issuer:** iTrust Luxembourg

---

## 1 Introduction

### 1.1 Context

hestIA is a Retrieval-Augmented Generation (RAG) backend service developed by iTrust Luxembourg. It provides a REST API enabling client applications to ingest organizational documents into a vector knowledge base and query that knowledge base through a hosted Large Language Model. The system is designed for multi-tenant deployments in which document collections are owned by organizations and access is governed by a classification-level model aligned with information security management requirements.

This Interface Control Document describes the external interface presented by the hestIA API to integrating systems, frontend clients, and administrative tooling. It is intended for system integrators, frontend developers, security reviewers, and certification authorities.

### 1.2 Objectives

This document aims to:

- Formally describe the logical interface structure of hestIA without duplicating the auto-generated OpenAPI specification.
- Define authentication and authorization contracts that integrating parties must satisfy.
- Specify error handling conventions and expected response shapes.
- Document integration constraints, timeout parameters, and deployment assumptions relevant to interfacing parties.
- Provide a reference integration flow illustrating end-to-end usage.

This document does not describe internal implementation details, database schemas, or algorithmic specifics beyond what is required for external integration.

For system-level architecture and design principles, refer to the hestIA Functional Architecture Document.

### 1.3 Document Structure

| Section | Title | Content Summary |
|---|---|---|
| 1 | Introduction | Context, objectives, acronyms, glossary |
| 2 | Software Overview | Functional description and architecture |
| 3 | Interfaces | API conventions, authentication, authorization, example flows |
| 4 | Error Handling | Error format, status codes, error catalogue |
| 5 | Versioning | Version policy and current status |
| 6 | Assumptions and Constraints | Deployment, configuration, and operational assumptions |
| 7 | Integration Guidelines | Practical guidance for integration teams |

### 1.4 Acronyms

| Acronym | Expansion |
|---|---|
| API | Application Programming Interface |
| BFF | Backend for Frontend |
| BM25 | Best Match 25 (probabilistic relevance ranking function) |
| CSP | Content Security Policy |
| DAG | Directed Acyclic Graph |
| DN | Distinguished Name (LDAP) |
| HNSW | Hierarchical Navigable Small World (vector index algorithm) |
| ICD | Interface Control Document |
| IdP | Identity Provider |
| ISMS | Information Security Management System |
| JWT | JSON Web Token |
| LDAP | Lightweight Directory Access Protocol |
| LDAPS | LDAP over SSL/TLS |
| LLM | Large Language Model |
| NDJSON | Newline-Delimited JSON |
| OIDC | OpenID Connect |
| RAG | Retrieval-Augmented Generation |
| RRF | Reciprocal Rank Fusion |
| SSE | Server-Sent Events |
| TLS | Transport Layer Security |
| WAL | Write-Ahead Logging (SQLite journal mode) |

### 1.5 Glossary

| Term | Definition |
|---|---|
| Collection | A named Qdrant namespace representing a knowledge base. Each collection is owned by exactly one organization and contains chunked, embedded documents. |
| Chunk | The atomic unit of document storage. A section of a parsed document, carrying dense and sparse vector embeddings, document metadata, and a classification level. |
| Classification Level | An integer from 0 (PUBLIC) to 4 (SECRET) assigned to a document or query result. Governs which users may retrieve which chunks. |
| Tenant | Synonym for Organization. A logical grouping of users that owns or has access to one or more collections. |
| Organization | A named entity in SQLite representing a business unit or department, identified by an integer ID and a short abbreviation. |
| Tenant Role | A role assigned to a user within a specific organization: `moderator`, `co-moderator`, or null (ordinary member). |
| Corpus | Per-collection BM25 vocabulary and document-frequency statistics, persisted to disk and used for sparse encoding at query time. |
| Execution Graph | A YAML-defined DAG of processing nodes (encode, retrieve, augment, generate) describing how a single RAG request is processed. |
| Must-Change Password | A flag on a user account (`must_change_pw`) indicating the client must redirect the user to a password-change screen before allowing further interaction. |
| Provider | A pluggable adapter implementing the LLMProvider protocol. Currently `vllm` and `ollama` are implemented. |
| Moderator | A tenant-role granting administrative rights within a single organization. |
| Collection Moderator | A user who moderates the organization that owns a given collection. Authorized to upload documents to and delete documents from that collection. |

---

## 2 Software Overview

### 2.1 Function and Purpose

hestIA provides the following logical functional groups.

#### 2.1.1 Identity, Access, and User Management

Covers all aspects of authentication, authorization, and user lifecycle management.

- **Authentication and Session Management:** Supports three mutually exclusive authentication modes (local, LDAP, OIDC). Issues short-lived signed JWT access tokens. Provides self-service account management (profile retrieval, password change). Enforces per-user account expiry and a mandatory-password-change workflow.
- **User Administration:** Provides user lifecycle management (create, read, update, delete) restricted to system administrators. Lists available roles.
- **Tenant and Collection Administration:** Provides organization lifecycle management (create, update, delete), membership management (add/remove users, assign tenant roles and classification levels), and collection access grant management. Accessible only to administrators and authorized moderators.
- **Conversation History:** Allows authenticated users to list, rename, and delete saved conversations, and to delete individual messages within a conversation.

#### 2.1.2 System Health and Discovery

Unauthenticated endpoints for operational monitoring and service introspection. Expose liveness and readiness probes, enumeration of available LLM models, and listing of available vector collections. Intended for use by infrastructure monitoring tools, load balancers, and client applications performing startup checks.

#### 2.1.3 Document Intelligence and Retrieval

Core knowledge-base functionality covering the full document lifecycle from ingestion to AI-assisted querying.

- **Document Ingestion:** Accepts structured and unstructured documents (`.docx`, `.pdf`, `.xlsx`, `.xlsm`, `.pptx`, `.json`, `.csv`, `.txt`, `.md`) via multipart upload. Parses documents to Markdown, extracts metadata, assigns a classification level, chunks content at section boundaries, generates dense and sparse embeddings, and stores the result in Qdrant. Optionally uses iTrust-specific parser variants for internal document templates. A non-persisting parse-and-preview endpoint is also provided.
- **Retrieval-Augmented Generation:** Provides single-turn prompt completion (`/api/generate`) and multi-turn chat (`/api/chat`). When a collection is specified, executes a hybrid semantic + keyword search, augments the user prompt with retrieved context, and forwards the augmented request to the configured LLM. Supports streaming responses and optional persistence of conversation history. Enforces classification-level filtering on retrieved chunks based on the requesting user's permissions.
- **Direct Vector Search:** Provides raw vector search against a named collection in three modes: semantic (dense cosine), keyword (sparse BM25), and hybrid (RRF fusion of both). Intended for integrating applications that manage their own retrieval logic.
- **Vector Encoding:** Exposes the internal embedding pipeline for external use: dense encoding via the configured embedding model, and sparse BM25 encoding against a named collection's corpus.

#### 2.1.4 Auxiliary Platform Services

Supporting services that complement core functionality but are not part of the primary data pipeline.

- **Help Content Management:** Provides a simple CMS for markdown-based help sections and associated images, readable by all authenticated users, writable by administrators only.

### 2.2 Architecture Overview

**Components**

| Component | Technology | Role |
|---|---|---|
| hestIA API | FastAPI (Python 3.13) | REST API server; RAG orchestration; business logic |
| hestia-ui | SvelteKit (Node.js 22) | Frontend application; communicates with API via server-side BFF routes |
| LLM Provider | vLLM or Ollama (external) | Text generation, embedding, and reranking |
| Vector Store | Qdrant (external) | Dense + sparse hybrid vector storage and retrieval |
| User Database | SQLite (embedded) | User accounts, roles, organizations, collection grants, conversation history |
| Identity Provider | Keycloak or LDAP server (optional, external) | OIDC or LDAP authentication when `AUTH_MODE` is not `local` |

**Runtime Dependencies**

The hestIA API process depends on:

- The Qdrant instance being reachable at `DB_URL` at startup.
- The LLM provider being reachable at `LLM_URL` / `EMB_URL` / `RRK_URL` when relevant services are activated.
- A writable filesystem path at `HESTIA_DATA_DIR` for the SQLite database and BM25 corpus files.
- The external IdP being reachable (LDAP or OIDC mode only); degraded IdP availability causes login failures.

**Data Flow Summary**

*Document ingestion path:*
> Client upload → Parse (format-specific parser) → Chunk (section splitter) → Dense encode (embedding model) → Sparse encode (BM25, in-process) → Upsert to Qdrant + persist corpus to disk

*Query / RAG path:*
> Client request → Policy check (ACL + classification filter) → Load execution graph template → Encode query (dense + sparse) → Hybrid retrieval from Qdrant (RRF) → Augment prompt (inject retrieved context) → LLM completion → Optionally stream response → Optionally persist conversation

*Authentication path:*
> Client credentials → AuthenticationService (local / LDAP / OIDC) → Issue JWT → Client presents JWT as Bearer token → `get_current_user` decodes JWT, loads full user profile + permissions from SQLite on every request

**Frontend–Backend Communication**

The SvelteKit frontend communicates with the hestIA API exclusively through server-side route handlers (BFF pattern). Browser JavaScript does not call the hestIA API directly. Accordingly, no CORS middleware is configured on the hestIA API.

---

## 3 Interfaces

### 3.1 Interface Specification

**OpenAPI Specification**

The hestIA API exposes a machine-readable OpenAPI 3.x specification at runtime:

| Endpoint | Description |
|---|---|
| `GET /openapi.json` | Full OpenAPI schema (JSON) |
| `GET /docs` | Swagger UI interactive documentation |
| `GET /redoc` | ReDoc rendered documentation |

The OpenAPI schema is the authoritative definition of all endpoints, request/response formats, and validation rules. In case of discrepancy, the OpenAPI definition takes precedence.

**Transport**

- Protocol: HTTP/1.1 over TCP. TLS termination is expected to occur at a reverse proxy layer; the hestIA process itself listens on plain HTTP (default port 5555).
- All request and response bodies use `application/json` unless otherwise specified.
- File upload endpoints use `multipart/form-data`.
- Streaming responses use newline-delimited JSON (NDJSON): each line is a complete JSON object terminated by `\n`.

Direct exposure of the API over plaintext HTTP is not permitted in production deployments.

**Request Conventions**

- A client may supply a `X-Request-ID` header with any string value. If supplied, the value is echoed in the response `X-Request-ID` header and included in server-side log records. If omitted, the server generates a UUID v4.
- All UUID path parameters are accepted in standard hyphenated format.
- Boolean query parameters use standard FastAPI/Python coercion: `true`/`false` or `1`/`0`.

**Response Conventions**

- Successful responses from core business endpoints use the envelope `{"data": <payload>, "error": null, "meta": {}}`.
- Health and administrative endpoints may return flat JSON without the envelope.
- Error responses follow the format defined in Section 4.

**Streaming Convention**

When a `generate` or `chat` request is made with `stream: true`:

1. Each yielded line is a JSON object `{"content": "<text fragment>"}` or `{"thinking": "<reasoning fragment>"}` for models that expose reasoning tokens.
2. After the content stream is exhausted, a final metadata line is yielded: `{"conversation_id": "...", "user_message_id": "...", "assistant_message_id": "...", "citations": [...], "thinking": "..."}`.
3. Clients must read to end-of-stream to obtain citation data and conversation identifiers.

**Pagination**

No pagination mechanism is currently implemented. List endpoints return complete result sets. This is noted as a constraint in Section 6.

**Conditional Endpoint Availability**

Several API endpoints are only registered when their backing service is configured at startup. Requests to endpoints belonging to an inactive service will return HTTP 404. The active services can be determined by inspecting the `GET /ready` response. Affected endpoint groups include: `/api/encode`, `/api/generate`, `/api/chat`, `/api/search`, `/api/parse`, `/api/upload`, and `/api/collections/**`.

### 3.2 Authentication

**Overview**

hestIA uses JWT Bearer token authentication. Tokens are obtained via one of the login flows described below and must be presented in the `Authorization: Bearer <token>` header on all protected endpoints.

**Token Properties**

| Property | Value |
|---|---|
| Token type | JSON Web Token (JWT), signed only (not encrypted) |
| Default signing algorithm | HS256 (configurable via `AUTH_ENCODING_ALGORITHM`) |
| Default lifetime | 360 minutes (6 hours); configurable via `AUTH_TOKEN_LIFETIME` |
| Payload claims | `sub` (user UUID in hex), `exp` (UTC expiry) |
| Refresh token | Not issued. A new token must be obtained by re-authenticating. |

**Login — Local and LDAP (`POST /login`)**

- Accepts `application/x-www-form-urlencoded` with fields `username` and `password` (OAuth2 Password flow).
- LDAP mode attempts local authentication first; on failure, falls back to the configured LDAP server.
- Rate-limited to 5 requests per minute per client IP by default. Exceeding this limit returns HTTP 429.
- Successful response shape: `{"access_token": "<jwt>", "token_type": "bearer", "must_change_pw": <bool>}`.

**Login — OIDC (Authorization Code Flow)**

The OIDC flow is a three-step sequence:

1. Client calls `GET /auth/oidc/authorize?redirect_uri=<uri>`. Server returns `{"url": "<provider_auth_url>", "state": "<token>"}`.
2. Client redirects the user agent to the provider URL.
3. Provider redirects back to the client with `code` and `state` parameters. Client submits these to `POST /auth/oidc/callback` with body `{"code": str, "redirect_uri": str, "state": str|null}`.
4. Server exchanges the code, provisions the user if required, and returns the same token envelope as `/login`.

OIDC logout is initiated by `GET /auth/oidc/logout?redirect_uri=<uri>`, which returns HTTP 302 to the provider's end-session endpoint.

**Must-Change Password Flag**

The `must_change_pw` boolean in every login response indicates that the user's account has been flagged for mandatory password change. Integrating clients must block further navigation and redirect to `PATCH /account/password` until this flag is cleared.

**Token Validation**

On every protected request, the server:

1. Extracts the Bearer token from the `Authorization` header.
2. Verifies the JWT signature and expiry using the server-side secret.
3. Loads the full user profile and computed permissions from the SQLite database. No caching is applied; permissions reflect the current state of the database on every request.

### 3.3 Authorization

**System Roles**

| Role | Description |
|---|---|
| `admin` | Full access to all endpoints and all collections. Bypasses all tenant and collection access checks. |
| `user` | Standard access. Subject to tenant membership and collection-level access controls. |

**Tenant Roles**

Each user may hold one of the following roles within a specific organization. Tenant roles are independent of system roles.

| Tenant Role | Permissions within the organization |
|---|---|
| `moderator` | Add/remove members; set classification levels; assign co-moderators; manage collection grants. At most one moderator per organization. |
| `co-moderator` | Add/remove members; manage collection grants. Cannot assign roles. |
| null (member) | Access to collections governed solely by the user's classification level within the organization. |

**Collection Access Control**

Access to a collection is determined by a two-layer model:

- **Layer 1 — Tenant grant:** A collection may be associated with multiple organizations with roles of `owner` or `access`. Each grant may carry an optional `max_classification` integer cap.
- **Layer 2 — User classification level:** Each user has an integer `classification_level` (0–4) per organization membership.

The effective maximum classification a user may retrieve is: `min(user_level, grant_cap)` when a cap is present; the user's own level otherwise. When a user belongs to multiple organizations that both have access to the same collection, the higher effective classification applies.

| Level | Label |
|---|---|
| 0 | PUBLIC |
| 1 | INTERNAL |
| 2 | RESTRICTED |
| 3 | CONFIDENTIAL |
| 4 | SECRET |

**Endpoint Authorization Summary**

| Endpoint Group | Minimum Requirement |
|---|---|
| `/health`, `/ready`, `/models`, `/collections` | None (unauthenticated) |
| `/login`, `/auth/oidc/**` | None (authentication endpoints) |
| `/account/**`, `/conversations/**`, `/help` (read), `/api/**` | Any authenticated user (valid JWT) |
| `/admin/users/**`, `/admin/roles` | `admin` system role |
| `/admin/organizations` (list), `/admin/collections/create` | `admin` or any tenant moderator |
| `/admin/organizations/{id}/**` (management) | `admin` or moderator of the specified org |
| `/api/upload`, collection deletion | `admin` or moderator of the collection's owner org |
| `/help` (write), `/help/images` (write) | `admin` system role |

### 3.4 Example Integration Flow

The following flow illustrates a complete integration scenario: an administrator uploads a document and a user subsequently queries it.

**Step 1 — Authenticate (Administrator)**

```
POST /login
Content-Type: application/x-www-form-urlencoded

username=admin_user&password=<password>
```

Response: `{"access_token": "<jwt_admin>", "token_type": "bearer", "must_change_pw": false}`

Store `jwt_admin` for subsequent requests.

**Step 2 — Verify System Readiness**

```
GET /ready
```

Confirm that `ingestion` and `generate` (or `search`) services appear in the active services list. If not, the upload and chat endpoints will return HTTP 404.

**Step 3 — Preview Document (Optional)**

```
POST /api/parse
Authorization: Bearer <jwt_admin>
Content-Type: multipart/form-data

file=<document.pdf>
itrust_template=false
```

Response: `{"metadata": {...}, "markdown": "...", "filename": "document.pdf"}`

Inspect the parsed metadata (title, version, classification) and markdown before committing. Apply any corrections as `metadata_overrides` in the next step.

**Step 4 — Upload Document**

```
POST /api/upload
Authorization: Bearer <jwt_admin>
Content-Type: multipart/form-data

file=<document.pdf>
collection=iso27001_policies
tenants=["org_security"]
itrust_template=false
metadata_overrides={"classification": "INTERNAL"}
language=english
```

Response: `{"ok": true, "collection": "iso27001_policies", "source": "document.pdf", "n_chunks": 42, "n_upserted": 42, "elapsed_ms": 3120.5}`

Verify that `n_chunks` equals `n_upserted`. A discrepancy indicates a partial ingestion failure.

**Step 5 — Authenticate (End User)**

```
POST /login
Content-Type: application/x-www-form-urlencoded

username=analyst_user&password=<password>
```

If `must_change_pw` is `true` in the response, redirect the user to `PATCH /account/password` before proceeding.

**Step 6 — Query the Knowledge Base (Streaming)**

```
POST /api/chat
Authorization: Bearer <jwt_user>
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "What are the access control requirements in our security policy?"}
  ],
  "collection": "iso27001_policies",
  "stream": true,
  "save_chat": true,
  "conversation_title": "Access Control Review"
}
```

The server streams NDJSON lines of `{"content": "..."}` fragments. The final line contains `{"conversation_id": "...", "citations": [...]}`. Parse the final metadata line to obtain citation references and the conversation identifier for subsequent turns.

**Step 7 — Continue Conversation**

Include prior conversation history in the `messages` array and pass the `conversation_id` from Step 6. The server will persist the updated conversation if `save_chat` remains `true`.

---

## 4 Error Handling

### 4.1 Standard Error Format

No unified custom error model is currently implemented. Error responses follow FastAPI defaults and therefore vary depending on the error source.

All error responses return a JSON body. The shape varies by error source:

**Domain errors (HestiaError subclasses):**

```json
{"detail": "<human-readable message>"}
```

**FastAPI validation errors (HTTP 422):**

```json
{
  "detail": [
    {"loc": ["body", "field_name"], "msg": "<description>", "type": "<error_type>"}
  ]
}
```

The `X-Request-ID` header is always present in the response and can be used to correlate the error with server-side log records.

### 4.2 Common Errors

| HTTP Code | Meaning | When It Occurs |
|---|---|---|
| 400 Bad Request | Invalid input | Malformed request body, invalid field values, OIDC not enabled when calling OIDC endpoints |
| 401 Unauthorized | Authentication failure | Missing or expired JWT, invalid token signature, user account not found |
| 403 Forbidden | Authorization failure | Insufficient system role, insufficient tenant role, no access to the requested collection |
| 404 Not Found | Resource not found | Endpoint not registered (service inactive), unknown collection, unknown user/org ID |
| 409 Conflict | State conflict | Attempting to assign a second moderator to a tenant that already has one |
| 413 Request Entity Too Large | Upload too large | File exceeds the configured body size limit (enforced at reverse proxy / SvelteKit layer) |
| 422 Unprocessable Entity | Schema validation failure | Missing required fields, wrong types, enum values not recognized |
| 429 Too Many Requests | Rate limit exceeded | More than the configured number of login attempts per minute from the same IP |
| 500 Internal Server Error | Unexpected server error | Unhandled exception, database error, missing configuration value |
| 502 Bad Gateway | Upstream provider error | LLM provider or Qdrant is unreachable or returns an error response |

---

## 5 Versioning

The current deployed version is **alpha_v0.3**, as declared in the FastAPI application metadata (`GET /openapi.json` → `info.version`).

No formal API versioning scheme (e.g., URI path versioning `/v1/`) has been implemented. The system is in an alpha development stage; breaking changes may occur between releases without prior deprecation notice during this phase.

As a consequence, backward compatibility is not guaranteed between releases at this stage.

Integrating parties should monitor the `info.version` field from `/openapi.json` as a change detection mechanism. A formal versioning and deprecation policy is not yet defined; this is noted as a constraint in Section 6.

---

## 6 Assumptions and Constraints

**Deployment Assumptions**

- The hestIA API process runs behind a reverse proxy or load balancer that handles TLS termination. The API itself listens on plain HTTP (default port 5555).
- The BFF pattern is assumed: browser clients communicate with the hestIA API only through the SvelteKit server-side layer. Direct browser-to-API calls are not supported, and no CORS configuration is present.
- Qdrant and the LLM provider are assumed to be reachable on private network addresses. No mutual TLS between hestIA and Qdrant/LLM is defined.

**Authentication Constraints**

- No refresh token is issued. Sessions expire after the configured lifetime (default 6 hours) and require re-authentication.
- Account-level expiry (`expires_at`) is enforced only at login time for local authentication. A token issued before expiry remains valid until its own `exp` claim passes.
- Role expiry timestamps (`user_roles.expires_at`) are stored in the database but are not currently enforced at runtime.

**Authorization Constraints**

- Permissions are recomputed from the database on every authenticated request. There is no permission cache.
- System roles are restricted to exactly two values (`admin`, `user`). Custom roles are not supported.
- Each organization may have at most one `moderator` tenant role holder at a time.

**Data and Storage Constraints**

- All user, organizational, and conversation data is stored in a single SQLite file. SQLite WAL mode is enabled, but write concurrency is limited under high load. No horizontal scaling of the user database is supported.
- Uploaded files are processed in memory and not retained after ingestion. There is no document retrieval endpoint; re-ingestion is required to update a document.
- Multimodal message content (images) is not persisted. Only text content is stored in the SQLite `messages` table.
- No server-side file size limit is enforced in the Python API layer. The effective upload limit is determined by the SvelteKit `BODY_SIZE_LIMIT` environment variable (example value: `15M`). This must be configured at the infrastructure layer.

**Functional Constraints**

- Pagination is not implemented on any list endpoint.
- Document ingestion is blocking within the HTTP request lifecycle (executed via `asyncio.to_thread`). Large document ingestion will hold the HTTP connection open for the duration of processing.
- Conversation history is limited to the last 10 message pairs sent to the LLM (configurable via `MAX_HISTORY_PAIRS`). Older messages are stored in SQLite but not included in LLM context.
- Rate limiting is applied only to the `/login` endpoint. No rate limiting is applied to LLM, ingestion, or search endpoints.
- No formal versioning or backward-compatibility guarantee exists at the current `alpha_v0.3` stage.

---

## 7 Integration Guidelines

**Obtaining and Storing Tokens**

Tokens must be stored securely. In browser-based applications using the SvelteKit BFF, tokens must be held server-side (e.g., in an HTTP-only session cookie) and never exposed to browser JavaScript. Re-authenticate before or immediately after the `exp` claim is reached, as no refresh token endpoint exists.

**Handling the Must-Change Password Flag**

All login response handlers must inspect `must_change_pw`. If `true`, gate further API usage and present a password change flow (`PATCH /account/password`) before proceeding. Failure to enforce this flag may allow users to access the system with a compromised or administrator-assigned password.

**Checking Service Availability Before First Use**

Call `GET /ready` during application startup or health check routines. If a required service (e.g., `ingestion`, `generate`) is absent from the response, the corresponding endpoints will return HTTP 404. Do not treat a 404 on `/api/upload` or `/api/chat` as an authorization error; check readiness first.

**Streaming Response Handling**

When calling `/api/chat` or `/api/generate` with `stream: true`:

1. Consume the response as a stream of newline-delimited JSON objects.
2. Do not close the connection prematurely; citation data and conversation identifiers are only available in the final metadata line.
3. Handle the `{"thinking": "..."}` line type gracefully (may be discarded or displayed depending on UX requirements).

**Collection Access Verification**

Before presenting a collection to an end user as a selectable option, call `GET /api/collections`. This endpoint returns only the collections visible to the authenticated user, applying permission filtering for non-administrators. Do not use the unauthenticated `GET /collections` (health router) endpoint for authenticated user interfaces, as it returns all collections without permission filtering.

**Document Ingestion Workflow**

The recommended sequence for document upload UIs:

1. Call `POST /api/parse` with the file to obtain metadata and a markdown preview.
2. Present the parsed metadata to the user for review and optional correction.
3. Submit the confirmed upload via `POST /api/upload` with `metadata_overrides` carrying any user corrections.

This two-step approach avoids persisting documents with incorrect metadata.

**Error Handling Strategy**

- HTTP 401: clear the stored token and redirect the user to the login flow.
- HTTP 403: definitive access denial; do not retry without an authorization change.
- HTTP 502: transient upstream failure; implement exponential backoff with a maximum retry budget.
- HTTP 429 on `/login`: present the user with a wait message; the lockout duration is configurable server-side (default 5 minutes).
- Log the `X-Request-ID` from every response; include it in support requests to enable server-side log correlation.

**OIDC Integration**

The `redirect_uri` supplied to `/auth/oidc/authorize` must exactly match the URI submitted to `/auth/oidc/callback`. The server does not validate the `state` parameter at the callback step — integrating parties are responsible for state validation on the client side to protect against CSRF attacks on the authorization flow.

**Secrets Management**

The following values must be supplied via environment variables with appropriate secret management tooling and must not appear in source control or container image layers:

| Variable | Purpose |
|---|---|
| `AUTH_SECRET_KEY` | JWT signing secret (minimum 32 characters) |
| `LLM_API_KEY` | Bearer token for the LLM provider |
| `DB_API_KEY` | API key for the Qdrant instance |
| `OIDC_CLIENT_SECRET` | OIDC client secret |
| `LDAP_APP_DN` / `LDAP_APP_PASSWORD` | LDAP service account credentials |
