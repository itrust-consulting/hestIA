# User Manual

## Table of Contents

1. [What is hestIA?](#1-what-is-hestia)
2. [Getting Started](#2-getting-started)
3. [Using the Chat Interface](#3-using-the-chat-interface)
4. [Working with Documents](#4-working-with-documents)
5. [Administration](#5-administration)
6. [Security & Privacy](#6-security--privacy)
7. [Troubleshooting](#7-troubleshooting)
8. [Glossary](#8-glossary)

---

## 1. What is hestIA?

hestIA is an on-premises enterprise AI assistant. If you have used ChatGPT, Microsoft Copilot, or similar tools, the experience will feel familiar: you type a question in plain language and receive a conversational answer. The difference is that hestIA runs entirely within your organisation's own infrastructure — no data ever leaves your environment — and it adds a layer that general-purpose chatbots do not offer: the ability to ground answers in your organisation's own documents.

**Key characteristics:**

- **General-purpose AI** — use it for drafting, summarising, explaining, translating, brainstorming, or any other task you would bring to a typical AI assistant.
- **On-premises** — all data, models, and processing stay within your organisation's infrastructure. Nothing is sent to external cloud services.
- **Enterprise knowledge base** — organisations can build and maintain curated document collections. When you ask a question that relates to those documents, hestIA draws its answer from them and provides inline citations so you can verify every claim.
- **Enforced classification** — users only receive insights from documents they are authorised to see, based on classification levels set by administrators and moderators. These levels typically reflect the organisation's own information security or data governance policies (e.g., public, internal, confidential, restricted).
- **Full audit trail** — all queries and responses are logged for compliance purposes.

**Current limitations:** hestIA does not perform web searches or connect to external services. Answers outside the scope of your organisation's indexed documents rely on the model's general knowledge.

### 1.1 Typical Use Cases

| Scenario | How hestIA helps |
|---|---|
| **Onboarding new employees** | New hires can ask questions about processes, tools, and policies in plain language instead of reading through extensive documentation. |
| **Policy and process reminders** | Quickly recall the steps for a specific process or the rules that apply to a given situation. |
| **Compliance verification** | Check whether a planned action or decision aligns with internal policies or regulations, with citations pointing to the relevant clauses. |
| **Cross-organisation knowledge sharing** | One organisation can grant another access to a collection — for example, sharing regulatory guidelines with a partner — while retaining full control over the maximum classification level the partner can access. |
| **Day-to-day AI assistance** | Use hestIA for any general task: drafting emails, summarising meeting notes, explaining technical concepts, and more. |

---

## 2. Getting Started

### 2.1 Prerequisites

- A modern web browser (Chrome, Firefox, Edge, Safari).
- A user account created by your administrator, or credentials from your organisation's directory (LDAP / SSO).

### 2.2 Logging In

Navigate to the hestIA URL provided by your administrator.

**Local accounts:** Enter your username and password, then click **Log in**.

**SSO / OIDC:** If your organisation uses single sign-on (e.g., Keycloak), click the SSO button on the login page and authenticate through your organisation's identity provider.


### 2.3 Changing Your Password

Go to **Account → Overview** in the top navigation. Enter your current password and your new password, then save. Password changes take effect immediately.

### 2.4 Joining a Tenant

You can only query a department's or team's documents once you're a member of the corresponding tenant. This happens one of two ways:

- **Invitation** — a tenant moderator invites you directly. You'll see the invitation among your account notifications and can accept or decline it.
- **Self-service request** — if you know which tenant you need, you can file a join request yourself; a moderator of that tenant reviews it and approves or rejects it.

Until you're a member of a tenant, you can still use hestIA for general-purpose questions, but you won't get answers grounded in that tenant's documents.

---

## 3. Using the Chat Interface

After login you are taken to the **Chat** page. This is your main workspace.

### 3.1 Starting a Conversation

Type your question or request in the input field at the bottom of the screen and press **Enter** (or click the send button). hestIA streams a response. If the answer draws on indexed document collections, it will include inline citations.

You can use hestIA for anything you would use a general AI assistant for — drafting text, explaining concepts, summarising content, and more. When your question relates to your organisation's documents, hestIA will automatically search the collections you have access to and ground its answer in them.

**Tips for good questions:**

- Be specific. "What is the reimbursement limit for business travel in Germany?" works better than "What are the travel rules?".
- When querying company documents, use the language those documents are written in for best results.
- If you receive a vague or unhelpful answer, try rephrasing or adding more context.
- For compliance questions, ask hestIA to cite the relevant policy clause so you can verify the source.

### 3.2 Reading Cited Responses

When an answer draws on your organisation's document collections, it includes inline citation markers linked to the specific source passages. Click a citation to view the excerpt and the document it came from. Use these references to verify the information before acting on it — particularly for policy or compliance questions.

Answers that do not involve indexed documents (general-purpose questions) will not carry citations and rely on the model's trained knowledge.

> hestIA can be wrong. Always cross-check critical information against the original source document.

### 3.3 Attaching Files

You can upload a file directly into the chat to ask questions about it. Supported formats are listed in [Section 4.1](#41-supported-file-formats). The file is processed within your session and is not permanently indexed unless an administrator adds it to a collection.

### 3.4 Conversation History

Previous conversations are listed in the left sidebar. Click any conversation to resume it. Conversations are private to your account.

---

## 4. Working with Documents

### 4.1 Supported File Formats

The following file types can be ingested into document collections or attached in chat:

| Format | Extension |
|---|---|
| PDF | `.pdf` |
| Word document | `.docx` |
| Excel spreadsheet | `.xlsx`, `.xlsm` |
| PowerPoint presentation | `.pptx` |
| Plain text | `.txt` |
| CSV | `.csv` |
| Markdown | `.md`, `.markdown` |
| JSON | `.json` |

### 4.2 How Documents Are Indexed

When a document is added to a collection, hestIA reads and splits it into passages, converts those passages into vector embeddings, and stores them in a vector database. At query time, your question is matched against these embeddings to retrieve the most relevant passages, which are then used to compose the answer.

This process means that **document updates are not automatic** — if a source document changes, an administrator must re-ingest it for the new version to be reflected in answers.

### 4.3 Document Visibility

You can only query documents that belong to collections your tenant membership grants you access to. If you believe a document should be available but is not, contact your administrator or moderator.

---

## 5. Administration

This section is intended for users with the **admin** role or **tenant moderator** role.

### 5.1 Role Overview

Roles work on two independent levels: a **platform role** (`admin` or `user`) that is the
same everywhere, and an optional **tenant role** (`moderator` or `co-moderator`) that only
applies within one specific tenant a person belongs to. Someone with no tenant role in a
given tenant is simply a **member** of it.

| Role | Level | Scope | Capabilities |
|---|---|---|---|
| `admin` | Platform | Everywhere | Full access: users, roles, tenants, collections |
| `user` | Platform | Everywhere | The default platform role; further capabilities come entirely from tenant membership |
| `moderator` | Tenant | One tenant | Manage that tenant's members and their access levels |
| `co-moderator` | Tenant | One tenant | Assist the moderator with tenant management |
| _member (no tenant role)_ | Tenant | One tenant | Query collections that tenant has access to |

### 5.2 User Management (Admin)

Navigate to **Admin → Users**.

- **Create a user:** Click **New user**, fill in the username, email, and initial password, and assign a role.
- **Edit a user:** Click the user row to update their details, role, or expiration date.
- **Delete a user:** Use the action menu on the user row. This permanently removes the account — hestIA does not currently support disabling an account without deleting it.

> When using LDAP or OIDC, user accounts are created automatically on first login. You can still edit roles and expiration dates from this panel.

### 5.3 Tenant Management (Admin)

Tenants represent organisational units (departments, teams, projects). Navigate to **Admin → Tenants**.

- **Create a tenant:** Provide a name and optionally assign a moderator.
- **Add members:** Select the tenant, then add users and set their classification level.
- **Grant collection access:** In the tenant view, link a collection and set the access type (`owner` or `access`).

### 5.4 Collection Management (Admin)

Collections are groups of documents. Navigate to **Admin → Collections**.

- **Create a collection:** Provide a name and description.
- **Upload documents:** Open the collection and use **Upload** to add files. The system will parse and index them automatically.
- **Remove documents:** Select documents and use the delete action. Their passages are removed from the vector index.
- **Grant tenant access:** Link tenants to the collection so their members can query it.

### 5.5 Tenant Moderation

Moderators manage members within their assigned tenant without needing full admin access. From **Admin → Tenants**, a moderator can:

- Add and remove members.
- Adjust member classification levels.
- Assign or revoke the co-moderator role.
- Invite specific users to join the tenant, or review and approve/reject self-service join requests.
- Request access to another tenant's collection, and approve or reject incoming requests from other tenants for collections their own tenant owns.

---

## 6. Security & Privacy

### 6.1 Data Residency

All document processing, model inference, and data storage occur within your organisation's own infrastructure. hestIA does not connect to external AI services.

### 6.2 Audit Logging

Security-relevant events — queries, responses, logins, and administrative changes — are written to a structured audit log as metadata (who did what, and when): the actual text of a query or response is never written to the audit log. Login/logout auditing is off by default and must be turned on by an administrator. Logs are stored locally and can be forwarded to your organisation's SIEM or log management system. Contact your administrator for log access.

### 6.3 Access Control

Access to documents is enforced at query time based on:

1. **Tenant membership** — which organisational unit you belong to.
2. **Collection assignment** — which collections that tenant can access.
3. **Classification level** — your personal classification ceiling within the tenant.

A user who is not a member of a tenant, or whose classification level is insufficient, will not receive answers drawn from the restricted documents, even if they know the documents exist. This enforcement is automatic and transparent: hestIA simply answers as if those documents do not exist for that user.

**Cross-organisation sharing:** Tenant moderators (or administrators) can grant an external tenant (e.g., a partner organisation) access to a collection while setting a maximum classification level for that tenant. This allows controlled knowledge sharing — for example, publishing regulatory guidelines to partners — without exposing content above the permitted classification ceiling. The external organisation's users interact with the shared collection exactly like any other, subject to their own individual classification levels and the cap set by the owning organisation.

### 6.4 Authentication Modes

hestIA supports three authentication modes, configured by your administrator:

| Mode | Description |
|---|---|
| Local | Usernames and hashed passwords stored in the local database |
| LDAP | Authentication against an existing directory service |
| OIDC | Single sign-on via an identity provider (e.g., Keycloak) |

---

## 7. Troubleshooting

### "I get an error when I log in"

- Verify that Caps Lock is off and that you are using the correct username format (some LDAP setups require `user@domain` or `DOMAIN\user`).
- If using SSO, confirm your identity provider session has not expired.
- Contact your administrator to confirm your account is active and has not expired.

### "My question returns a very general answer with no citations"

- If you expected an answer grounded in company documents, the relevant document may not have been indexed yet. Contact your administrator to check which collections are available.
- Try rephrasing the question. Very short or ambiguous questions may not match the right passages in the index.
- Ensure you are a member of the tenant that has access to the relevant collection.
- If the question is general-purpose (not document-related), a lack of citations is expected behaviour — hestIA is answering from its trained knowledge.

### "The answer cites a document I cannot open"

- You may lack direct file-system access to the source document. hestIA shows you the passage it used; ask your administrator for access to the full file if needed.

### "A recently updated document still shows old content"

- hestIA indexes documents at upload time. If the source has changed, an administrator must re-upload the updated version for the index to reflect it.

### Who to contact

For account issues, contact your **system administrator**. For questions about which documents are available, contact your **tenant moderator**.

---

## 8. Glossary

| Term | Plain-language definition |
|---|---|
| **RAG** (Retrieval-Augmented Generation) | A technique where the AI retrieves relevant passages from a document index before generating an answer, so the response is grounded in real content rather than the model's training data alone. |
| **Collection** | A curated set of documents that have been indexed and made available for querying. |
| **Tenant** | An organisational unit (e.g., a department or team) used to group users and control which collections they can access. |
| **Embedding** | A numerical representation of text that captures its meaning, allowing similar passages to be found by a search. |
| **Vector database** | A specialised database that stores embeddings and enables fast similarity search across large document sets. |
| **Classification level** | A per-user, per-tenant access tier that restricts which documents within a collection a user may query. |
| **Join request** | A user-initiated request to become a member of a specific tenant; reviewed and approved or rejected by a moderator of that tenant. |
| **Invitation** | A moderator-initiated invite for a specific user to join their tenant; the invited user accepts or declines it. |
| **Share request** | A moderator-initiated request for their tenant to be granted access to another tenant's collection; approved or rejected by a moderator of the owning tenant. |
| **Citation** | A reference in the AI's response pointing to the specific source passage the information was drawn from. |
| **LDAP** | Lightweight Directory Access Protocol — a standard for accessing corporate directory services (e.g., Active Directory). |
| **OIDC** | OpenID Connect — a standard protocol for single sign-on authentication. |
| **Audit log** | A tamper-evident record of all actions taken within the system, used for compliance and incident investigation. |
