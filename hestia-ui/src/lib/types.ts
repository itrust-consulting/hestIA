export type Org = { id: number; name: string; abbreviation: string };
export type AccessGrant = Org & { max_classification: number | null };

export type CollectionDocument = {
  source: string;
  source_uri: string;
  uploaded_by: string;
  uploaded_at: string;
  chunk_count: number;
  doc_info: Record<string, string>;
};

/** Mirrors the raw Qdrant point payload (see Chunk.to_payload() in
 *  hestia/domain/rag/chunk.py) — shown as-is in the document detail view. */
export type DocumentChunk = {
  id: string;
  content: string;
  token_count: number | null;
  source: string;
  source_uri: string;
  uploaded_by: string;
  uploaded_at: string;
  previous: string | null;
  next: string | null;
  info: { header?: string; path?: string; level?: number; position?: number; part?: number };
  doc_info: Record<string, string>;
  access: { classification: number | null };
};

export type DocumentDetail = {
  source_uri: string;
  doc_info: Record<string, string>;
  chunks: DocumentChunk[];
};

export type Collection = {
  id: string;
  points_count: number;
  status: string;
  ownerTenant: Org | null;
  access: AccessGrant[];
  documents: CollectionDocument[];
  /** Document count for list views that don't need the full `documents`
   *  array (avoids fetching/scrolling every collection's full point list
   *  just to render a count). Only `documents.length` is populated
   *  instead on the detail page, which needs the real array. */
  documentCount?: number;
};

export type Citation = {
  key: string;
  source: string;
  subject: string;
  path: string;
  excerpt: string;
};

export type ContentPart =
  | { type: 'text'; text: string }
  | { type: 'image_url'; image_url: { url: string } };

export type Role = 'user' | 'assistant' | 'system';
export type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  apiContent?: string | ContentPart[];
  images?: string[];
  attachments?: { name: string; size?: number; markdown?: string }[];
  citations?: Citation[];
  thinking?: string;
  /** Elapsed thinking time in seconds, frozen once real content starts
   *  arriving (or the stream ends). Computed client-side from wall-clock
   *  timestamps in actions.ts — set once and never recomputed, so it
   *  survives the id swap from a local temp id to the persisted message id. */
  thinkingSecs?: number;
  /** True when generation was interrupted by the user clicking Stop (or the
   *  stream otherwise aborted) rather than finishing normally -- drives a
   *  "Generation stopped" note instead of implying the reply is complete. */
  stopped?: boolean;
  /** True when this turn's history was over budget and the server is
   *  folding it before it can start generating -- swaps the "Thinking"
   *  placeholder's label to "Compacting…". */
  compacting?: boolean;
  createdAt: number;
  /** Set only for messages loaded from the server; absent for messages pushed
   *  live this session (not yet round-tripped through a fetch). Used to build
   *  resume cursors for sliding-window eviction — never evict a message without one. */
  rowid?: number;
};
export type APIMessage = { role: Role; content: string | ContentPart[] };
export type ChatAPIMessages = APIMessage[];
export type ChatResponse = { response: string };
export type Conversation = { id: string; title: string; createdAt: number; updatedAt?: number; };

export type CollectionPermission = { access: boolean; max_classification: number | null };

export type Permissions = {
    allowed_collections: Record<string, CollectionPermission>;
    user_management: boolean;
    system_management: boolean;
    data_management: boolean;
    extra: Record<string, unknown>;
    // Backend-pending fields used by admin/mod guards — currently undefined until
    // the backend adds them to the Permissions model.
    is_admin?: boolean;
    moderated_tenants?: number[];
};

export type UserRole = { id: number; name: string };
export type UserOrg  = { id: number; name: string; abbr: string };

export type User = {
    id: string;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    roles: UserRole[];
    orgs: UserOrg[];
    permissions: Permissions;
    must_change_pw: boolean;
    auth_source: string;
    created_at: number;
    updated_at: number;
    expires_at: number | null;
};
