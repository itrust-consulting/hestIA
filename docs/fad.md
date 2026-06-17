# Functional Architecture Document (FAD)

Service: hestIA
Version: alpha_v0.3
Classification: INTERNAL
Date: 2026-06-15
Issuer: iTrust Luxembourg

---

## 1 Introduction

### 1.1 Context
hestIA is an on-premises AI assistance platform developed by itrust for IT governance and compliance (ISMS) use cases. It operates as an orchestration and logic layer positioned between end-user interfaces and a set of managed infrastructure services, mediating all access to AI generation, vector knowledge bases, and identity stores. This document elaborates the functional architecture of hestIA, complementing the System Concept Document (SCD) and Interface Control Document (ICD).

### 1.2 Objectives
This Functional Architecture Document (FAD) describes what hestIA does in functional terms: the functions it provides, the data it processes, the workflows it supports, and the constraints it enforces. It does not describe implementation technology, deployment topology, or internal algorithms. The FAD serves as the authoritative reference for functional completeness assessment, requirements traceability, and verification planning.

### 1.3 Document Structure

| Section | Title | Content Summary |
|---------|-------|-----------------|
| 1 | Introduction | Context, objectives, and document guide |
| 2 | Functional Overview | Functional scope and domain decomposition |
| 3 | Functional Decomposition | Component inventory and per-component functional descriptions |
| 4 | Functional Data Flows | High-level and per-scenario data flows; data object catalogue |
| 5 | Functional Workflows | User-level logical sequences for principal use cases |
| 6 | Functional Dependencies | Inter-function dependency table and critical dependency descriptions |
| 7 | Assumptions and Constraints | Functional constraints bounding system behaviour |

---

## 2 Functional Overview

### 2.1 Functional Scope
hestIA provides a managed AI assistance capability over organisationally controlled document corpora, enforcing classification-based access control at every interaction. The system accepts document uploads, transforms them into retrievable knowledge, and responds to user queries by synthesising retrieved knowledge with AI-generated language. It supports multi-tenant operations, ensuring that knowledge visibility is governed by organisational membership and individually assigned classification clearance levels. All interactions — document ingest, query, administration, and conversation management — are subject to authentication and policy enforcement without exception.

### 2.2 Functional Domains

| Domain | Description |
|--------|-------------|
| Identity and Access | Authentication of users via configurable credential schemes; issuance and validation of session tokens; role and classification-level assignment; execution of access policy decisions on every request |
| Document Intelligence | Ingestion of heterogeneous document formats; extraction of content and metadata; segmentation into addressable knowledge units; semantic and keyword encoding for retrieval |
| AI Interaction | Orchestrated AI workflows for single-turn generation and multi-turn conversational queries; retrieval-augmented prompt construction; AI response generation and delivery |
| Knowledge Management | Storage and lifecycle management of document collections; retrieval of knowledge units using hybrid search; conversation history persistence and management |
| Administration | Lifecycle management of users, organisations, collection grants, and organisational memberships; help content management |
| Observability | Structured system logging with request traceability; security audit logging of all sensitive actions; health and readiness status exposure |
| Extensibility | Registration and invocation of domain-specific agent tools within orchestrated workflows; composable workflow graph definition without platform modification |

---

## 3 Functional Decomposition

### 3.1 Functional Components

| Function ID | Name | Description |
|-------------|------|-------------|
| FC-01 | API Gateway | Single system entry point; authenticates all inbound requests; assigns correlation identifiers; routes requests to appropriate functions |
| FC-02 | Authentication | Validates user credentials via one of three configurable modes (local, directory, federated); issues and validates short-lived session tokens |
| FC-03 | Access Policy Enforcement | Evaluates per-request access decisions based on platform roles, organisational membership, and document classification clearance; returns ALLOW, FILTER, or DENY decisions |
| FC-04 | Request Handling | Receives authenticated and authorised requests; selects workflow templates; drives workflow execution; persists conversation outcomes; emits audit entries |
| FC-05 | Workflow Orchestration | Executes declaratively defined directed execution graphs; coordinates typed processing nodes in sequence or composition |
| FC-06 | Document Ingestion | Accepts source documents; extracts text and structural metadata; segments content into chunks; encodes chunks for storage in the knowledge base |
| FC-07 | Document Retrieval | Executes hybrid knowledge base queries using encoded query vectors subject to access-policy-derived constraints; returns ranked result sets |
| FC-08 | Prompt Augmentation | Constructs augmented prompts by formatting retrieved knowledge chunks with citation keys and combining them with the user query |
| FC-09 | AI Generation | Delegates prompt execution to the LLM Server; supports single-turn and multi-turn modes; delivers streaming and non-streaming responses; handles reasoning-model output |
| FC-10 | Conversation Management | Persists, loads, and manages multi-turn conversation histories per user; supports conversation lifecycle operations and bounded context window loading |
| FC-11 | Document Preview | Parses an uploaded document without persisting it; returns extracted metadata and a structured content preview for pre-ingestion review |
| FC-12 | Direct Vector Search | Exposes knowledge base search in semantic, keyword, and hybrid modes for integrators managing their own retrieval workflows |
| FC-13 | Vector Encoding Exposure | Exposes the encoding pipeline externally for dense semantic embedding and sparse keyword vectorisation against a specified collection corpus |
| FC-14 | User Administration | Manages the full lifecycle of user accounts: creation, retrieval, update, deactivation |
| FC-15 | Organisation and Membership Administration | Manages tenant organisations and their membership: creation, update, member add/remove, role and classification-level assignment |
| FC-16 | Collection Grant Administration | Manages which organisations have access to which document collections and under what conditions |
| FC-17 | Help Content Management | Manages a set of markdown-based help sections and associated images; readable by all authenticated users; writable by administrators only |
| FC-18 | Logging and Audit | Emits structured system logs with correlation identifiers; records security-relevant audit events to a dedicated, persisted audit trail |
| FC-19 | Health and Readiness | Exposes unauthenticated liveness and readiness status; reports active services and available models and collections |

---

### 3.2 Functional Descriptions

**FC-01 — API Gateway**
- Description: The single functional entry point to hestIA. Every inbound interaction passes through this function before reaching any other.
- Inputs: All inbound requests from user interfaces or integrating systems.
- Outputs: Authenticated, correlated requests routed to the appropriate downstream function; error responses for unauthenticated or malformed requests.
- Behaviour: Assigns a unique correlation identifier to each request and propagates it through the processing chain. Invokes FC-02 to validate session tokens on all protected operations. Rejects requests that fail authentication before routing. Passes health and readiness probes directly to FC-19 without authentication.

---

**FC-02 — Authentication**
- Description: Verifies the identity of users and issues session tokens, supporting three mutually exclusive credential validation modes: local credential store, directory service (LDAP/Active Directory), and federated identity (OIDC).
- Inputs: User credentials (username and password, or directory-bound credentials, or OIDC exchange artefacts); bearer tokens on subsequent requests.
- Outputs: Short-lived JWT access tokens on successful authentication; validation outcome (valid/invalid) on token verification; error responses for failed, expired, or rate-limited attempts.
- Behaviour: Applies rate limiting to login attempts to mitigate brute-force attacks. Enforces account expiry. Triggers mandatory-password-change flows where required. Validates JWT signatures, expiry, and subject identity on every protected request. Only one authentication mode is active per deployment.

---

**FC-03 — Access Policy Enforcement**
- Description: Evaluates whether a requesting user is permitted to perform a requested operation and, if so, whether retrieval results must be filtered by classification level.
- Inputs: Authenticated user identity with associated roles, organisational memberships, and per-collection classification levels; the target resource and operation.
- Outputs: A policy decision of ALLOW, FILTER, or DENY. FILTER decisions carry a maximum classification constraint applied to retrieval queries.
- Behaviour: Applies a two-layer policy model. The first layer evaluates the platform-level role (administrator or user). The second layer evaluates the user's tenant role (moderator, co-moderator, member) and their assigned classification level within the relevant organisation. Policy is evaluated on every request; no caching of decisions is performed. Access to a collection requires both an active organisational grant (FC-16) and a user classification level meeting or exceeding the document's classification. DENY outcomes terminate request processing before any knowledge base or AI interaction occurs.

---

**FC-04 — Request Handling**
- Description: Coordinates the processing of AI assistance requests after authentication and policy enforcement. Selects the appropriate workflow template, drives workflow execution, manages conversation persistence, and records audit events.
- Inputs: Authenticated and policy-cleared request containing query text, workflow mode, conversation context reference, and optional parameters.
- Outputs: AI-generated response (streamed or complete); persisted conversation record (if requested); audit log entry.
- Behaviour: Selects from four workflow templates — generate (single-turn, no retrieval), rag_generate (single-turn with retrieval), chat (multi-turn, no retrieval), rag_chat (multi-turn with retrieval) — based on request parameters. Loads bounded conversation history from FC-10 when operating in multi-turn modes. Passes the assembled context to FC-05 for execution. After generation, optionally persists the exchange to the conversation history. Emits a structured audit entry for every AI interaction.

---

**FC-05 — Workflow Orchestration**
- Description: Executes directed execution graphs defined declaratively as YAML artefacts. Each graph is composed of typed processing nodes; the engine traverses the graph, invoking each node function in dependency order.
- Inputs: A resolved workflow graph; the input context assembled by FC-04 (query, history, policy filters, parameters).
- Outputs: The accumulated result context after full graph traversal, including generated response, retrieved chunks, and citation map.
- Behaviour: Supports the following node types in current-generation workflows: EncodeDense (query semantic encoding), EncodeSparse (query keyword encoding), Retrieve (knowledge base query via FC-07), Augment (prompt construction via FC-08), Generate (single-turn AI invocation via FC-09), Chat (multi-turn AI invocation via FC-09). Additionally accommodates extensibility node types — ToolCall, Branch, QueryStructured — for agentic workflows. Graphs are composable; new workflow patterns can be registered without modifying platform logic.

---

**FC-06 — Document Ingestion**
- Description: Transforms source documents into encoded knowledge units stored in the knowledge base. Supports a range of document formats and maintains collection-scoped encoding metadata.
- Inputs: Source document file; metadata (title, subject, classification level, source URI, target tenants, target collection); optional metadata overrides.
- Outputs: A set of encoded chunks upserted to the Vector Database; updated collection corpus statistics.
- Behaviour: Parses source files in the following formats: PDF, DOCX, XLSX, XLSM, PPTX, JSON, CSV, TXT, Markdown. Extracts text content, structural hierarchy, and document-level metadata. Applies any caller-supplied metadata overrides. Segments the document into chunks at section boundaries; each chunk carries a reference to its source document, its position in the document structure, and navigation links to adjacent chunks. Encodes each chunk using both dense semantic and sparse keyword vectorisation. Upserts the resulting vectors and metadata payloads to the Vector Database. Updates corpus statistics used for keyword scoring within the collection.

---

**FC-07 — Document Retrieval**
- Description: Queries the knowledge base to identify the most relevant chunks for a given encoded query, subject to access-policy-derived constraints.
- Inputs: Encoded query vectors (dense and/or sparse); access policy filter (maximum classification constraint from FC-03); target collection identifier; retrieval parameters (result count, mode).
- Outputs: A ranked list of chunk payloads including content, source reference, classification level, and position metadata.
- Behaviour: Supports three retrieval modes: semantic (dense vector similarity), keyword (sparse vector matching), and hybrid (fusion of both). In hybrid mode, results from semantic and keyword searches are merged using a reciprocal rank fusion strategy. Access policy filters are applied as hard payload constraints, ensuring that chunks whose classification exceeds the user's clearance are excluded at the retrieval layer, not post-hoc. Returns a ranked list bounded by the requested result count.

---

**FC-08 — Prompt Augmentation**
- Description: Constructs the augmented prompt that combines retrieved knowledge with the user query, enabling the AI generation function to produce grounded, citable responses.
- Inputs: Ranked list of retrieved chunks (from FC-07); original user query text; citation configuration.
- Outputs: An augmented prompt containing structured knowledge context, a source citation map keyed to context entries, and the user query.
- Behaviour: Formats each retrieved chunk with a citation key. Assembles a structured context block from the formatted chunks. Builds a source map associating each citation key with its document source name, subject, and excerpt. Combines the context block, source map, and user query into the final augmented prompt passed to FC-09.

---

**FC-09 — AI Generation**
- Description: Invokes the LLM Server to produce a natural language response from a prepared prompt, operating in either single-turn or multi-turn mode.
- Inputs: Prepared prompt (plain or augmented); optional message history (multi-turn mode); generation parameters (model, temperature, etc.); streaming preference.
- Outputs: Generated response text; optional citations list (derived from the source map); optional thinking-token content (for reasoning-model outputs); delivery in streaming (NDJSON) or non-streaming form.
- Behaviour: Selects the invocation mode (generate vs. chat) according to the workflow node type. In multi-turn mode, includes the bounded message history in the LLM context. Supports streaming delivery to the caller, emitting response fragments progressively as they are produced by the LLM Server. Correctly processes thinking-token streams produced by reasoning-capable models, separating reasoning traces from final response content. Returns a structured result carrying the response text, citations, and any reasoning trace.

---

**FC-10 — Conversation Management**
- Description: Persists and manages multi-turn conversation histories, enabling continuity across interactions and bounded context loading for AI generation.
- Inputs: Messages (role, content, citations, thinking) to be persisted; conversation identifiers for retrieval and lifecycle operations; user identity.
- Outputs: Stored conversation records; retrieved conversation lists and message histories; updated or deleted records.
- Behaviour: Creates new conversations with a system-generated or user-supplied title. Appends user and assistant messages to conversation records after each exchange. Loads the most recent N message pairs (default: 10) for inclusion in the LLM context window; full conversation history is retained in storage regardless of the context window limit. Supports renaming conversations, deleting conversations, and deleting individual messages. Conversation records are scoped to the owning user.

---

**FC-11 — Document Preview**
- Description: Parses an uploaded document and returns a preview of extracted content and metadata without persisting any data to the knowledge base.
- Inputs: Source document file.
- Outputs: Extracted document metadata (title, subject, structural summary); Markdown-formatted content preview.
- Behaviour: Applies the same parsing logic as FC-06 but performs no encoding, no storage, and no corpus update. Intended to support a review-before-ingest workflow in which an authorised user can inspect what hestIA will extract from a document before committing it to a collection.

---

**FC-12 — Direct Vector Search**
- Description: Exposes knowledge base search capabilities directly for integrators or workflows that manage their own retrieval logic independently of the standard AI assistance workflows.
- Inputs: Query text or pre-encoded query vectors; retrieval mode (semantic, keyword, or hybrid); target collection; retrieval parameters; access credentials.
- Outputs: Ranked list of matching chunks with payloads, scored and ordered by relevance.
- Behaviour: Applies the same retrieval logic and access-policy filtering as FC-07. Returns raw ranked results without prompt augmentation or AI generation. Access control constraints are enforced identically to standard query flows.

---

**FC-13 — Vector Encoding Exposure**
- Description: Exposes the encoding pipeline to external callers, allowing them to obtain semantic or keyword vector representations of arbitrary text against a specific collection corpus.
- Inputs: Input text; encoding mode (dense or sparse); target collection identifier (for sparse encoding corpus reference).
- Outputs: Dense vector representation (high-dimensional float array) for dense mode; sparse vector representation (weighted term-index pairs) for sparse mode.
- Behaviour: Dense encoding produces a semantic embedding via the LLM Server embedding capability. Sparse encoding produces a keyword-weighted vector using the collection-scoped corpus statistics maintained by FC-06. Outputs are structurally compatible with the vectors stored in the knowledge base, enabling external systems to form queries or perform comparisons.

---

**FC-14 — User Administration**
- Description: Manages the full lifecycle of user accounts within the platform.
- Inputs: User account data (username, credentials, roles, metadata); user identifiers for retrieval, update, and deactivation operations.
- Outputs: Created, retrieved, updated, or deactivated user records.
- Behaviour: Restricted to users holding the administrator platform role. Supports creation of new user accounts with initial role assignment. Supports retrieval of individual or all user records. Supports update of account attributes including credential resets and role changes. Supports account deactivation. Changes to user records take effect on the next request evaluated by FC-03, as no permission caching exists.

---

**FC-15 — Organisation and Membership Administration**
- Description: Manages tenant organisations and the membership of users within them, including the assignment of organisational roles and document classification clearance levels.
- Inputs: Organisation data (name, metadata); membership operations (user identifier, target organisation, role, classification level).
- Outputs: Created or updated organisation records; updated membership records reflecting added/removed members and their assigned roles and clearance levels.
- Behaviour: Organisation creation and configuration are restricted to administrators. Membership management (adding or removing members, assigning tenant roles of moderator, co-moderator, or member, and setting per-user classification levels from 0 to 4) may be performed by administrators or by users holding the moderator role within the target organisation. Classification levels assigned here directly govern which document chunks are visible to that user during retrieval, as enforced by FC-03 and FC-07.

---

**FC-16 — Collection Grant Administration**
- Description: Manages the authorisation grants that permit organisations to access specific document collections.
- Inputs: Grant configuration specifying the target collection and the target organisation; administrator credentials.
- Outputs: Active or revoked collection grants recorded in the User Store.
- Behaviour: Restricted to administrators. An organisation must hold an active grant on a collection before any of its members can query or ingest documents into that collection. Grant revocation immediately affects subsequent policy evaluations by FC-03, as decisions are not cached.

---

**FC-17 — Help Content Management**
- Description: Manages a set of contextual help resources, comprising markdown-formatted help sections and associated image assets.
- Inputs: Help section content (markdown text, section identifier); image assets; read requests from authenticated users.
- Outputs: Stored or updated help section records; help section listings and content for read operations; stored image assets.
- Behaviour: Read access (listing and retrieval of help sections and images) is available to all authenticated users. Write operations (create, update, delete sections and images) are restricted to administrators. Functions as a lightweight, in-platform content management capability requiring no external CMS dependency.

---

**FC-18 — Logging and Audit**
- Description: Provides two complementary logging capabilities: structured operational system logging for traceability and debugging, and a dedicated security audit trail for compliance and incident investigation.
- Inputs: Log emission requests from all other functions, carrying correlation identifiers, event types, resource references, user identities, and outcomes.
- Outputs: Structured JSON system log entries written to the system log; audit event records written to a dedicated audit log file and persisted in the User Store.
- Behaviour: System logs carry the correlation identifier assigned by FC-01, enabling full request traceability across all functions. Audit logs capture security-relevant events in six categories: authentication events, document access events, AI interaction events, data modification events, administrative actions, and policy decisions. Audit records include user identifier, action type, timestamp, target resource, and outcome. Audit log writes are unconditional and cannot be suppressed by request parameters.

---

**FC-19 — Health and Readiness**
- Description: Exposes unauthenticated status endpoints allowing infrastructure orchestration systems and operators to assess the operational state of hestIA.
- Inputs: Liveness probe requests; readiness probe requests; service and capability enumeration requests.
- Outputs: Liveness status indicator; readiness status indicator reflecting the availability of all registered dependent services; lists of active services, available AI models, and accessible collections.
- Behaviour: Liveness and readiness are independent signals. Readiness reflects the aggregate availability of conditionally registered external services (LLM Server, Vector Database, User Store). Service registration is dynamic; readiness degrades if any registered service becomes unavailable. Model and collection listings are derived from live queries to the respective services. These endpoints do not require authentication and are excluded from audit logging.

---

## 4 Functional Data Flows

### 4.1 High-Level Data Flow
All interactions with hestIA originate at FC-01 (API Gateway), which authenticates requests via FC-02 and routes them to the appropriate function. For AI assistance interactions, FC-04 (Request Handling) drives a workflow via FC-05 (Workflow Orchestration), which coordinates encoding, retrieval, augmentation, and generation in sequence. Document ingestion interactions pass through FC-06, which transforms source files into encoded chunks and persists them to the knowledge base. Administrative interactions are handled by FC-14 through FC-17 under administrator or moderator authority. FC-03 (Access Policy Enforcement) is invoked on every interaction that touches protected resources, and FC-18 (Logging and Audit) receives emissions from every function throughout the request lifecycle.

### 4.2 Core Data Flows

#### 4.2.1 Authentication Flow

![Authentication Flow](./_figures/fad_seq_auth.svg)

1. The user presents credentials to FC-01.
2. FC-01 routes the request to FC-02 without policy evaluation.
3. FC-02 validates the credentials against the configured credential mode (local store, directory service, or federated provider).
4. FC-02 checks for account expiry and mandatory-password-change conditions.
5. On valid credentials, FC-02 issues a short-lived JWT token carrying the user subject identifier and expiry.
6. The token is returned to the user.
7. On all subsequent requests, the user presents the JWT as a Bearer token.
8. FC-01 passes the token to FC-02 for signature and expiry validation.
9. FC-02 returns the validated user identity, which FC-01 uses to load the user's roles and permissions from the User Store.
10. The enriched identity is passed to FC-03 for policy evaluation before the request proceeds.
11. FC-18 records authentication events (success, failure, rate-limit trigger) as audit entries.

#### 4.2.2 Document Ingestion Flow

![Document Ingestion Flow](./_figures/fad_seq_ingestion.svg)

1. An authorised user (holding a moderator role on the target organisation) submits a document upload request to FC-01, including the source file, target collection, target tenants, and classification level.
2. FC-01 authenticates the request via FC-02.
3. FC-03 evaluates whether the user holds the moderator role for the collection's owning organisation and whether an active collection grant exists; a DENY decision terminates processing.
4. FC-06 receives the document and invokes the parser for the appropriate format, extracting text content, document structure, and metadata.
5. Any caller-supplied metadata overrides are applied to the extracted metadata.
6. FC-06 segments the parsed content into chunks at section boundaries; each chunk is linked to its neighbours and annotated with source and position metadata.
7. FC-06 requests dense encoding for each chunk from the LLM Server embedding capability.
8. FC-06 requests sparse encoding for each chunk, updating the collection corpus statistics.
9. FC-06 upserts each chunk — comprising content, metadata, and both vector representations — to the Vector Database.
10. FC-18 records the ingestion event as an audit entry.

#### 4.2.3 Knowledge Query (RAG) Flow

![Knowledge Query (RAG) Flow](./_figures/fad_seq_rag.svg)

1. An authenticated user submits a query request to FC-01, specifying query text, target collection, and optionally a conversation reference and workflow parameters.
2. FC-01 authenticates the request via FC-02.
3. FC-03 evaluates the user's access to the target collection against their organisational membership and classification clearance. The decision is ALLOW, FILTER (carrying a maximum classification constraint), or DENY.
4. A DENY decision terminates processing; an ALLOW or FILTER decision proceeds.
5. FC-04 selects the appropriate workflow template (rag_generate or rag_chat) and loads bounded conversation history from FC-10 if operating in multi-turn mode.
6. FC-05 receives the assembled context and begins graph traversal.
7. FC-05 invokes EncodeDense: the query is encoded as a dense semantic vector via the LLM Server.
8. FC-05 invokes EncodeSparse: the query is encoded as a sparse keyword vector against the collection corpus.
9. FC-05 invokes Retrieve (FC-07): hybrid search is executed in the Vector Database using both vectors, with the classification filter from FC-03 applied as a hard constraint. A ranked list of chunks is returned.
10. FC-05 invokes Augment (FC-08): the retrieved chunks are formatted with citation keys, a source map is constructed, and the augmented prompt is assembled with the user query.
11. FC-05 invokes Generate or Chat (FC-09): the augmented prompt and optional message history are sent to the LLM Server, which returns a response.
12. FC-09 delivers the response to the user in streaming or non-streaming form.
13. FC-04 optionally persists the user message and assistant response to the conversation history via FC-10.
14. FC-18 records the AI interaction and document access events as audit entries.

### 4.3 Data Objects

| Data Object | Description |
|-------------|-------------|
| Document | Source file and its associated metadata: title, subject, classification level, source URI, and assigned tenants |
| Chunk | Atomic knowledge unit derived from a document section: content text, source reference, structural path, position index, adjacent-chunk navigation links, classification level, dense vector, and sparse vector |
| Dense Vector | High-dimensional floating-point array representing the semantic content of a chunk or query |
| Sparse Vector | Keyword-weighted term index representation of a chunk or query, scored against the collection corpus vocabulary |
| Query | A search request comprising one or both vector forms and optional payload filters, targeting a specific collection |
| Execution Graph | A YAML-defined directed acyclic graph of typed processing nodes specifying a complete AI workflow |
| User | Platform account record: unique identifier, username, platform role, organisational memberships (each carrying tenant role and classification level) |
| Permission | Derived access descriptor for a user: map of permitted collections to maximum classification level per collection |
| Policy Result | The outcome of a per-request access evaluation: ALLOW, FILTER (with classification constraint), or DENY |
| Conversation | A persistent, user-scoped record comprising a title and an ordered sequence of messages |
| Message | A single turn in a conversation: role (user or assistant), content text, optional citations list, optional thinking text |
| JWT Token | A signed, short-lived token carrying the user subject identifier and expiry, issued by FC-02 |
| Citation | A structured reference associating a citation key with a source document name, subject, and content excerpt |
| Audit Entry | A security event record: user identifier, action type, timestamp, target resource, and outcome |
| Corpus | Per-collection vocabulary and document-frequency statistics used for keyword vector scoring |

---

## 5 Functional Workflows

### 5.1 Document Ingestion Workflow

![Document Ingestion Workflow](./_figures/fad_wf_ingestion.svg)

1. An authenticated user with the moderator role on the target organisation initiates a document ingestion request, supplying the source document, target collection, classification level, and tenant assignments.
2. The system validates the user's authority to ingest into the specified collection (moderator role check and active collection grant check).
3. The system parses the document, extracting text and structural metadata. The user may optionally preview the extraction result via the Document Preview function (FC-11) before proceeding.
4. The user may supply or confirm metadata overrides (title, subject, classification, source URI).
5. The system segments the document into chunks, preserving section structure and navigation links.
6. The system encodes each chunk using both semantic and keyword vectorisation methods.
7. The system stores the encoded chunks in the knowledge base under the specified collection, with all metadata and classification attributes.
8. The system confirms successful ingestion. An audit record is created.
9. The ingested content is immediately available for retrieval by users with appropriate access.

### 5.2 Knowledge Query Workflow

![Knowledge Query Workflow](./_figures/fad_wf_query.svg)

1. An authenticated user submits a natural language query, optionally within an existing conversation context, targeting a collection they have access to.
2. The system evaluates the user's access policy for the target collection. If denied, the query is rejected. If filtered, a classification ceiling is applied to subsequent retrieval.
3. The system encodes the query for retrieval.
4. The system retrieves the most relevant knowledge chunks from the collection using hybrid search, applying any classification filter.
5. The system constructs an augmented prompt combining the retrieved context (with citation keys) and the user query.
6. In multi-turn mode, the system includes a bounded set of prior conversation messages in the prompt context.
7. The system submits the augmented prompt to the AI generation service and delivers the response to the user, with streaming if requested.
8. The response includes a citations list keyed to the retrieved source documents.
9. If conversation persistence is requested, the user message and assistant response are appended to the conversation history.
10. An audit record is created capturing the interaction, the user identity, and the accessed resources.

### 5.3 Administration Workflow

![Administration Workflow](./_figures/fad_wf_admin.svg)

**User Management:**
1. An administrator creates a new user account, specifying credentials and the initial platform role.
2. The administrator may subsequently update account attributes (role, credentials) or deactivate the account.
3. All changes take effect immediately on the next request evaluated against that user's identity.

**Organisation and Membership Management:**
1. An administrator creates a new organisation (tenant), assigning it a name and configuration.
2. The administrator or an organisational moderator adds users to the organisation, assigning each a tenant role (moderator, co-moderator, or member) and a document classification clearance level (0 to 4).
3. Roles and clearance levels may be updated at any time. Changes affect subsequent access policy evaluations immediately.
4. Members may be removed from the organisation, revoking their access to collections granted to that organisation.

**Collection Grant Management:**
1. An administrator grants a specific organisation access to a specific collection, creating an active grant record.
2. From that point, members of the organisation — subject to their individual classification levels — may query documents in that collection.
3. The administrator may revoke a grant, immediately preventing further access by the organisation's members.

**Help Content Management:**
1. An administrator creates or updates help sections by supplying markdown content and a section identifier.
2. Administrators may upload image assets for use within help sections.
3. All authenticated users may read help sections and images at any time.

---

## 6 Functional Dependencies

### 6.1 Dependency Table

| Function | Depends On |
|----------|------------|
| FC-01 API Gateway | FC-02 (token validation on every request), FC-19 (health/readiness pass-through) |
| FC-02 Authentication | User Store (credential validation, account state, profile retrieval, audit persistence) |
| FC-03 Access Policy Enforcement | FC-02 (validated identity), User Store (membership and grant records) |
| FC-04 Request Handling | FC-03 (policy decision), FC-05 (workflow execution), FC-10 (conversation history), FC-18 (audit emission) |
| FC-05 Workflow Orchestration | FC-07 (retrieval node), FC-08 (augmentation node), FC-09 (generation node) |
| FC-06 Document Ingestion | FC-03 (moderator authority check), LLM Server (dense encoding), Vector Database (chunk storage), Corpus store (sparse encoding statistics) |
| FC-07 Document Retrieval | Vector Database (chunk search), FC-03 (classification filter input) |
| FC-08 Prompt Augmentation | FC-07 (ranked chunk list) |
| FC-09 AI Generation | LLM Server (text generation), FC-08 (augmented prompt, in RAG modes) |
| FC-10 Conversation Management | User Store (conversation and message persistence) |
| FC-11 Document Preview | Document parsing capability (shared with FC-06, non-persisting) |
| FC-12 Direct Vector Search | FC-03 (access policy filter), FC-07 (retrieval execution), Vector Database |
| FC-13 Vector Encoding Exposure | LLM Server (dense embedding), Corpus store (sparse encoding statistics) |
| FC-14 User Administration | FC-03 (administrator role check), User Store (user record persistence) |
| FC-15 Organisation and Membership Administration | FC-03 (role check), User Store (organisation and membership record persistence) |
| FC-16 Collection Grant Administration | FC-03 (administrator role check), User Store (grant record persistence) |
| FC-17 Help Content Management | FC-03 (role check for writes), User Store or equivalent content store |
| FC-18 Logging and Audit | User Store (audit record persistence); receives emissions from all other functions |
| FC-19 Health and Readiness | LLM Server, Vector Database, User Store (availability probes) |

### 6.2 Dependency Description

**Access Policy as a cross-cutting dependency:** FC-03 is invoked by every function that accesses protected resources. It is the single enforcement point for both platform RBAC and the tenant classification model. Any function that bypasses FC-03 would constitute a security gap; the architecture does not permit such bypass paths.

**User Store as the authoritative identity and history source:** FC-02, FC-03, FC-10, FC-14, FC-15, FC-16, and FC-18 all depend on the User Store. It holds user accounts, credentials, organisational memberships, collection grants, conversation histories, and audit records. Its availability is therefore necessary for the vast majority of system functions.

**LLM Server as the AI capability source:** FC-06 (dense encoding during ingestion), FC-09 (text generation), and FC-13 (encoding exposure) all depend on the LLM Server. Its unavailability prevents document ingestion encoding, query encoding, and all AI generation. FC-19 reflects LLM Server availability in its readiness signal.

**Vector Database as the knowledge persistence layer:** FC-06 (upsert) and FC-07 (retrieval) both depend on the Vector Database. Without it, no knowledge ingestion or retrieval is possible. FC-19 reflects its availability in the readiness signal.

**Corpus statistics as a local dependency of sparse encoding:** The sparse keyword encoding used in FC-06 and FC-13 depends on per-collection corpus statistics maintained on the platform's local storage. These statistics are updated with each ingestion; their loss or corruption would degrade keyword retrieval quality without preventing semantic retrieval.

**FC-05 as the composition orchestrator:** All RAG and generation workflows execute through FC-05. It has no external infrastructure dependencies of its own but depends on the functions it coordinates (FC-07, FC-08, FC-09). Its correct operation depends on the validity and integrity of the registered execution graph definitions.

---

## 7 Assumptions and Constraints

**A-01** — All requests to protected functions must carry a valid, non-expired JWT token issued by FC-02. No protected function may be accessed without prior authentication, regardless of request origin.

**A-02** — Access policy (FC-03) is evaluated on every request touching protected resources. Permission decisions are never cached between requests. Any change to user roles, membership, or collection grants takes effect on the immediately following request.

**A-03** — A user may access documents in a collection only if two independent conditions are simultaneously satisfied: the user's organisation holds an active grant for that collection, and the user's individual classification clearance level equals or exceeds the classification level of the target document chunks.

**A-04** — The three authentication modes (local, directory service, federated identity) are mutually exclusive. Exactly one mode is active per deployment. Mixed-mode authentication within a single deployment is not supported.

**A-05** — The authentication-disabled mode (ENABLE_AUTH=false) must not be activated in production deployments. It is provided solely for development and integration testing purposes.

**A-06** — Document ingestion into a collection requires the requesting user to hold the moderator role within the organisation that owns the collection. Members and co-moderators may not ingest documents.

**A-07** — Conversation history supplied to the LLM context window is bounded (default: 10 message pairs). Full conversation history is retained in persistent storage and is not subject to this bound.

**A-08** — Login attempts are rate-limited. No other functional endpoint is rate-limited at the current development stage.

**A-09** — List operations (users, conversations, collections, etc.) return all records without pagination. This constraint is acknowledged as a scalability limitation at the current alpha stage.

**A-10** — The hestIA API does not provide formal versioning or backward-compatibility guarantees at the alpha stage. Interfaces may change between versions without deprecation notice.

**A-11** — Validation of OIDC state parameters and PKCE flows during federated authentication is the responsibility of the integrating client application, not of hestIA.

**A-12** — Classification clearance levels are assigned as integer values on the scale 0 (PUBLIC) through 4 (SECRET). A user with clearance level N may access documents with classification levels 0 through N inclusive.

**A-13** — Audit logging is unconditional and non-suppressible. All security-relevant events — authentication, document access, AI interactions, data modifications, administrative actions, and policy decisions — are recorded regardless of request outcome.

**A-14** — Execution graph definitions are the authoritative specification of AI workflow behaviour. Changes to workflow behaviour are effected by modifying graph definitions; platform logic is not modified for workflow changes.

**A-15** — The platform does not perform OIDC identity provider discovery autonomously. OIDC provider configuration must be supplied at deployment time.
