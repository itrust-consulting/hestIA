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
  createdAt: number;
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
