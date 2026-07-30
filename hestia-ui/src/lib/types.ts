export type Org = { id: number; name: string; abbreviation: string };
export type AccessGrant = Org & { max_classification: number | null };

export type CollectionDocument = {
  source: string;
  source_uri: string;
  uploaded_by: string;
  uploaded_at: string;
  chunk_count: number;
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
  /** True while the server is compacting conversation context before this
   *  turn's real generation begins; drives the "Compacting…" label instead
   *  of the generic "Thinking" placeholder. Stops mattering once thinking or
   *  content starts arriving, never explicitly cleared. */
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
