import sqlite3
import threading
import uuid

BUSY_TIMEOUT_MS = 5000


def create_sqlite_connection(db_path: str) -> tuple[callable, callable, threading.Lock]:
    _local = threading.local()
    _lock = threading.Lock()

    def get_conn() -> sqlite3.Connection:
        conn = getattr(_local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS};")
            _local.conn = conn
        return conn

    def close():
        conn = getattr(_local, "conn", None)
        if conn is not None:
            conn.close()
            _local.conn = None

    return get_conn, close, _lock


def with_txn(fn):
    def wrapper(self, *args, **kwargs):
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute("BEGIN;")
                result = fn(self, conn, *args, **kwargs)
                conn.commit()
                return result
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
    return wrapper


class UserRepository:

    def __init__(self, get_conn: callable, db_lock: threading.Lock):
        self._get_conn = get_conn
        self._db_lock = db_lock

    @with_txn
    def initialize(self, conn: sqlite3.Connection):
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id                    BLOB(16) PRIMARY KEY,
              username              TEXT NOT NULL UNIQUE,
              email                 TEXT NOT NULL UNIQUE,
              first_name            TEXT NOT NULL,
              last_name             TEXT NOT NULL,
              password_hash         BLOB NOT NULL,
              salt                  BLOB NOT NULL,
              auth_source           TEXT NOT NULL,
              must_change_pw        INTEGER NOT NULL DEFAULT 1,
              created_at            INTEGER NOT NULL,
              updated_at            INTEGER NOT NULL,
              expires_at            INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS roles (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                description         TEXT
            );

            CREATE TABLE IF NOT EXISTS organizations (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                abbreviation        TEXT NOT NULL UNIQUE,
                created_at          INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_orgs (
                user_id             BLOB(16) NOT NULL,
                org_id              INTEGER NOT NULL,
                PRIMARY KEY         (user_id, org_id),
                FOREIGN KEY         (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY         (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_roles(
                user_id             BLOB(16) NOT NULL,
                role_id             INTEGER NOT NULL,
                starts_at           INTEGER NOT NULL,
                expires_at          INTEGER DEFAULT NULL,
                PRIMARY KEY         (user_id, role_id),
                FOREIGN KEY         (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY         (role_id) REFERENCES roles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tenant_collections (
                org_id              INTEGER NOT NULL,
                collection_id       TEXT NOT NULL,
                PRIMARY KEY         (org_id, collection_id),
                FOREIGN KEY         (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );

            INSERT OR IGNORE INTO roles (name, description) VALUES
                ('admin', 'Full system access'),
                ('user', 'Access to general system features');
            
            DELETE FROM roles WHERE name NOT IN ('admin', 'user');
            
            CREATE TABLE IF NOT EXISTS conversations (
              id                    BLOB(16) PRIMARY KEY,
              user_id               BLOB(16) NOT NULL,
              title                 TEXT,
              metadata_json         TEXT,
              created_at            INTEGER NOT NULL,
              updated_at            INTEGER NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
              id                    BLOB(16) PRIMARY KEY,
              c_id                  BLOB(16) NOT NULL,
              role                  TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
              metadata              TEXT,
              content               TEXT NOT NULL,
              options               TEXT,
              created_at            INTEGER NOT NULL,
              FOREIGN KEY (c_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_user_orgs ON user_orgs(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_roles ON user_roles(user_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(c_id, created_at, id);
            CREATE INDEX IF NOT EXISTS idx_tenant_collections ON tenant_collections(org_id);
            """
        )
        # executescript commits implicitly; run ALTER TABLE migrations separately
        for ddl in [
            "ALTER TABLE user_orgs ADD COLUMN classification_level INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE user_orgs ADD COLUMN tenant_role TEXT DEFAULT NULL",
            "ALTER TABLE tenant_collections ADD COLUMN role TEXT NOT NULL DEFAULT 'access'",
            "ALTER TABLE collection_tenants RENAME TO tenant_collections",
            "ALTER TABLE tenant_collections ADD COLUMN max_classification INTEGER DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN last_login_at INTEGER DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN last_seen_at INTEGER DEFAULT NULL",
        ]:
            try:
                conn.execute(ddl)
                conn.commit()
            except Exception:
                pass  # already migrated

    # ---- users ----

    def list_users(self) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT id, username, email, first_name, last_name, must_change_pw, auth_source, "
            "created_at, updated_at, expires_at, last_seen_at "
            "FROM users ORDER BY last_name ASC"
        ).fetchall()

    @with_txn
    def record_login(self, conn, *, id: uuid.UUID, ts: int):
        conn.execute("UPDATE users SET last_login_at = ?, last_seen_at = ? WHERE id = ?", (ts, ts, id.bytes))

    @with_txn
    def touch_last_seen(self, conn, *, id: uuid.UUID, ts: int):
        conn.execute("UPDATE users SET last_seen_at = ? WHERE id = ?", (ts, id.bytes))

    def get_user_activity(self, id: uuid.UUID) -> sqlite3.Row | None:
        """Last login/seen + conversation/message counts for one user --
        deliberately not part of list_users()'s SELECT (that's the
        frequently-loaded admin overview, kept cheap); this backs the
        per-user detail page's "Additional info" section instead."""
        return self._get_conn().execute(
            "SELECT u.last_login_at, u.last_seen_at, "
            "COUNT(DISTINCT c.id) AS conversation_count, COUNT(m.id) AS message_count "
            "FROM users u "
            "LEFT JOIN conversations c ON c.user_id = u.id "
            "LEFT JOIN messages m ON m.c_id = c.id "
            "WHERE u.id = ? GROUP BY u.id",
            (id.bytes,),
        ).fetchone()

    @with_txn
    def insert_user(self, conn, *, user_id: uuid.UUID, username: str, email: str,
                    first_name: str, last_name: str, auth_source: str,
                    password_hash: bytes, salt: bytes, must_change_pw: int,
                    created_ts: int, expires_ts: int | None = None):
        conn.execute(
            "INSERT INTO users (id, username, email, first_name, last_name, auth_source, "
            "password_hash, salt, must_change_pw, created_at, updated_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id.bytes, username, email, first_name, last_name, auth_source,
             password_hash, salt, must_change_pw, created_ts, created_ts, expires_ts),
        )

    @with_txn
    def delete_user(self, conn, *, id: uuid.UUID):
        conn.execute("DELETE FROM users WHERE id = ?", (id.bytes,))

    @with_txn
    def set_must_change_pw(self, conn, *, change: int, id: uuid.UUID, updated_ts: int):
        conn.execute("UPDATE users SET must_change_pw = ?, updated_at = ? WHERE id = ?",
                     (change, updated_ts, id.bytes))

    @with_txn
    def set_user_expiration(self, conn, *, id: uuid.UUID, expires_ts: int, updated_ts: int):
        conn.execute("UPDATE users SET expires_at = ?, updated_at = ? WHERE id = ?",
                     (expires_ts, updated_ts, id.bytes))

    @with_txn
    def update_username(self, conn, *, id: uuid.UUID, new_username: str, updated_ts: int):
        conn.execute("UPDATE users SET username = ?, updated_at = ? WHERE id = ?",
                     (new_username, updated_ts, id.bytes))

    @with_txn
    def update_user_email(self, conn, *, id: uuid.UUID, new_email: str, updated_ts: int):
        conn.execute("UPDATE users SET email = ?, updated_at = ? WHERE id = ?",
                     (new_email, updated_ts, id.bytes))

    @with_txn
    def update_user_profile(self, conn, *, id: uuid.UUID, username: str, email: str,
                            first_name: str, last_name: str, expires_ts: int | None, updated_ts: int):
        conn.execute(
            "UPDATE users SET username = ?, email = ?, first_name = ?, last_name = ?, "
            "expires_at = ?, updated_at = ? WHERE id = ?",
            (username, email, first_name, last_name, expires_ts, updated_ts, id.bytes),
        )

    @with_txn
    def update_user_password(self, conn, *, id: uuid.UUID, new_hash: bytes, new_salt: bytes, updated_ts: int):
        conn.execute("UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?",
                     (new_hash, new_salt, updated_ts, id.bytes))

    @with_txn
    def add_user_to_organization(self, conn, *, user_id: uuid.UUID, org_id: int):
        conn.execute("INSERT OR IGNORE INTO user_orgs (user_id, org_id) VALUES (?, ?)",
                     (user_id.bytes, org_id))

    @with_txn
    def remove_user_from_organization(self, conn, *, user_id: uuid.UUID, org_id: int):
        conn.execute("DELETE FROM user_orgs WHERE user_id = ? AND org_id = ?", (user_id.bytes, org_id))

    @with_txn
    def add_role_to_user(self, conn, *, user_id: uuid.UUID, role_id: int, starts_ts: int, expires_ts: int | None = None):
        conn.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id, starts_at, expires_at) VALUES (?, ?, ?, ?)",
                     (user_id.bytes, role_id, starts_ts, expires_ts))

    @with_txn
    def remove_role_from_user(self, conn, *, user_id: uuid.UUID, role_id: int):
        conn.execute("DELETE FROM user_roles WHERE user_id = ? AND role_id = ?", (user_id.bytes, role_id))

    def get_user_by_id(self, id: uuid.UUID) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, username, email, first_name, last_name, password_hash, salt, "
            "auth_source, must_change_pw, created_at, updated_at, expires_at FROM users WHERE id = ?",
            (id.bytes,),
        ).fetchone()

    def get_user_by_username(self, username: str) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, username, email, first_name, last_name, password_hash, salt, "
            "auth_source, must_change_pw, created_at, updated_at, expires_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    def get_user_by_email(self, email: str) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, username, email, first_name, last_name, password_hash, salt, "
            "auth_source, must_change_pw, created_at, updated_at, expires_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    def get_user_for_login(self, identifier: str) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, username, email, first_name, last_name, password_hash, salt, "
            "auth_source, must_change_pw, created_at, updated_at, expires_at "
            "FROM users WHERE username = ? OR email = ?",
            (identifier, identifier),
        ).fetchone()

    def get_user_roles(self, id: uuid.UUID) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT r.id, r.name, r.description, ur.starts_at, ur.expires_at "
            "FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = ?",
            (id.bytes,),
        ).fetchall()

    def get_user_organizations(self, id: uuid.UUID) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT o.id, o.name, o.abbreviation, o.created_at "
            "FROM user_orgs uo JOIN organizations o ON uo.org_id = o.id WHERE uo.user_id = ?",
            (id.bytes,),
        ).fetchall()

    # ---- organizations ----

    @with_txn
    def insert_organization(self, conn, *, name: str, abbreviation: str, created_ts: int):
        conn.execute("INSERT OR IGNORE INTO organizations (name, abbreviation, created_at) VALUES (?, ?, ?)",
                     (name, abbreviation, created_ts))

    @with_txn
    def update_organization(self, conn, *, id: int, name: str, abbreviation: str):
        conn.execute("UPDATE organizations SET name = ?, abbreviation = ? WHERE id = ?",
                     (name, abbreviation, id))

    @with_txn
    def delete_organization(self, conn, *, id: int):
        conn.execute("DELETE FROM organizations WHERE id = ?", (id,))

    def get_organization_by_name(self, name: str) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, name, abbreviation, created_at FROM organizations WHERE name = ?", (name,)
        ).fetchone()

    def get_organization_users(self, id: int) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT u.id, u.username, u.email, u.first_name, u.last_name, "
            "uo.classification_level, uo.tenant_role, u.last_seen_at "
            "FROM user_orgs uo JOIN users u ON uo.user_id = u.id WHERE uo.org_id = ?",
            (id,),
        ).fetchall()

    def list_organizations(self) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT id, name, abbreviation, created_at FROM organizations"
        ).fetchall()

    # ---- roles ----

    @with_txn
    def insert_role(self, conn, *, name: str, description: str):
        conn.execute("INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)", (name, description))

    @with_txn
    def delete_role(self, conn, *, id: int):
        conn.execute("DELETE FROM roles WHERE id = ?", (id,))

    def get_role_by_name(self, role: str) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, name, description FROM roles WHERE name = ?", (role,)
        ).fetchone()

    def get_role_by_id(self, id: int) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, name, description FROM roles WHERE id = ?", (id,)
        ).fetchone()

    def list_roles(self) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT id, name, description FROM roles ORDER BY id"
        ).fetchall()

    # ---- tenant memberships ----

    @with_txn
    def set_member_classification(self, conn, *, user_id: uuid.UUID, org_id: int, level: int):
        conn.execute("UPDATE user_orgs SET classification_level = ? WHERE user_id = ? AND org_id = ?",
                     (level, user_id.bytes, org_id))

    @with_txn
    def set_member_tenant_role(self, conn, *, user_id: uuid.UUID, org_id: int, role: str | None):
        conn.execute("UPDATE user_orgs SET tenant_role = ? WHERE user_id = ? AND org_id = ?",
                     (role, user_id.bytes, org_id))

    def get_user_org_memberships(self, user_id: uuid.UUID) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT org_id, classification_level, tenant_role FROM user_orgs WHERE user_id = ?",
            (user_id.bytes,)
        ).fetchall()

    def get_org_tenant_moderator(self, org_id: int) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT user_id FROM user_orgs WHERE org_id = ? AND tenant_role = 'moderator'", (org_id,)
        ).fetchone()

    # ---- tenant_collections ----

    def get_tenant_collections(self, org_id: int) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT collection_id, role, max_classification FROM tenant_collections WHERE org_id = ?", (org_id,)
        ).fetchall()

    def get_collection_owner(self, collection_id: str) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT o.id, o.name, o.abbreviation "
            "FROM tenant_collections tc JOIN organizations o ON tc.org_id = o.id "
            "WHERE tc.collection_id = ? AND tc.role = 'owner'",
            (collection_id,)
        ).fetchone()

    def get_collection_access_tenants(self, collection_id: str) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT o.id, o.name, o.abbreviation, tc.max_classification "
            "FROM tenant_collections tc JOIN organizations o ON tc.org_id = o.id "
            "WHERE tc.collection_id = ? AND tc.role = 'access'",
            (collection_id,)
        ).fetchall()

    @with_txn
    def add_tenant_collection(self, conn, *, org_id: int, collection_id: str, role: str = "access",
                              max_classification: int | None = None):
        if role == "owner":
            conn.execute(
                "DELETE FROM tenant_collections WHERE collection_id = ? AND role = 'owner' AND org_id != ?",
                (collection_id, org_id)
            )
        conn.execute(
            "INSERT OR REPLACE INTO tenant_collections (collection_id, org_id, role, max_classification) "
            "VALUES (?, ?, ?, ?)",
            (collection_id, org_id, role, max_classification)
        )

    @with_txn
    def remove_tenant_collection(self, conn, *, org_id: int, collection_id: str):
        conn.execute("DELETE FROM tenant_collections WHERE org_id = ? AND collection_id = ?",
                     (org_id, collection_id))

    @with_txn
    def remove_collection_grants(self, conn, *, collection_id: str):
        conn.execute("DELETE FROM tenant_collections WHERE collection_id = ?", (collection_id,))

    # ---- conversations ----

    @with_txn
    def insert_conversation(self, conn, *, conv_id: uuid.UUID, user_id: uuid.UUID,
                            title: str, metadata_json: str, ts: int):
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, metadata_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (conv_id.bytes, user_id.bytes, title, metadata_json, ts, ts),
        )

    def get_conversation_owner(self, c_id: uuid.UUID) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT user_id FROM conversations WHERE id = ?",
            (c_id.bytes,),
        ).fetchone()

    def get_conversation(self, user_id: uuid.UUID, limit: int, offset: int) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT id, title, metadata_json, created_at, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (user_id.bytes, limit, offset),
        ).fetchall()

    @with_txn
    def update_conversation_title(self, conn, *, user_id: uuid.UUID, c_id: uuid.UUID, title: str):
        conn.execute("UPDATE conversations SET title = ? WHERE id = ? AND user_id = ?",
                     (title, c_id.bytes, user_id.bytes))

    @with_txn
    def update_conversation_updated_at(self, conn, *, c_id: uuid.UUID, ts: int):
        conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (ts, c_id.bytes))

    def get_conversation_metadata(self, c_id: uuid.UUID) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT metadata_json FROM conversations WHERE id = ?",
            (c_id.bytes,),
        ).fetchone()

    @with_txn
    def update_conversation_metadata(self, conn, *, c_id: uuid.UUID, metadata_json: str):
        conn.execute("UPDATE conversations SET metadata_json = ? WHERE id = ?",
                     (metadata_json, c_id.bytes))

    @with_txn
    def delete_conversation(self, conn, *, user_id: uuid.UUID, c_id: uuid.UUID):
        conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?",
                     (c_id.bytes, user_id.bytes))

    # ---- messages ----

    @with_txn
    def insert_message(self, conn, *, msg_id: uuid.UUID, c_id: uuid.UUID, role: str,
                       metadata: str, content: str, options: str, ts: int):
        conn.execute(
            "INSERT INTO messages (id, c_id, role, metadata, content, options, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id.bytes, c_id.bytes, role, metadata, content, options, ts),
        )

    def get_messages(
        self,
        c_id: uuid.UUID,
        limit: int,
        before_created_at: int | None = None,
        before_rowid: int | None = None,
    ) -> list[sqlite3.Row]:
        if before_created_at is not None:
            return self._get_conn().execute(
                "SELECT id, role, metadata, content, options, created_at, rowid FROM messages "
                "WHERE c_id = ? AND (created_at < ? OR (created_at = ? AND rowid < ?)) "
                "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (c_id.bytes, before_created_at, before_created_at, before_rowid, limit),
            ).fetchall()
        return self._get_conn().execute(
            "SELECT id, role, metadata, content, options, created_at, rowid FROM messages "
            "WHERE c_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (c_id.bytes, limit),
        ).fetchall()

    def get_messages_after(
        self,
        c_id: uuid.UUID,
        after_created_at: int | None = None,
        after_rowid: int | None = None,
    ) -> list[sqlite3.Row]:
        """Ascending, unpaginated (no limit) — used for reconstructing full
        server-side history for LLM context, not for UI pagination."""
        if after_created_at is not None:
            return self._get_conn().execute(
                "SELECT id, role, metadata, content, options, created_at, rowid FROM messages "
                "WHERE c_id = ? AND (created_at > ? OR (created_at = ? AND rowid > ?)) "
                "ORDER BY created_at ASC, rowid ASC",
                (c_id.bytes, after_created_at, after_created_at, after_rowid),
            ).fetchall()
        return self._get_conn().execute(
            "SELECT id, role, metadata, content, options, created_at, rowid FROM messages "
            "WHERE c_id = ? ORDER BY created_at ASC, rowid ASC",
            (c_id.bytes,),
        ).fetchall()

    @with_txn
    def delete_message(self, conn, *, c_id: uuid.UUID, msg_id: uuid.UUID):
        conn.execute("DELETE FROM messages WHERE id = ? AND c_id = ?", (msg_id.bytes, c_id.bytes))
