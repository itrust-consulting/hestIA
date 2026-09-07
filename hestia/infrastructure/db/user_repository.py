import random
import sqlite3
import threading
import time
import uuid

BUSY_TIMEOUT_MS = 5000

# Retry/backoff for with_txn below. The in-process _db_lock already
# serializes every write from this process, so an OperationalError here can
# only come from a SEPARATE process holding the SQLite file lock (e.g. if
# this ever runs with multiple workers/replicas against the same db file) --
# these attempts are insurance against that, not against in-process
# contention, which busy_timeout/the lock already handle.
_TXN_RETRY_ATTEMPTS = 3
_TXN_RETRY_BASE_DELAY_S = 0.05


class ModeratorConflictError(Exception):
    """Raised when granting a join request would create a second tenant
    moderator. Kept as a repository-level exception (not a domain one) so
    this module stays free of a dependency on the domain layer -- callers
    translate it into whatever domain error fits their context."""


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
            for attempt in range(_TXN_RETRY_ATTEMPTS):
                try:
                    conn.execute("BEGIN;")
                    result = fn(self, conn, *args, **kwargs)
                    conn.commit()
                    return result
                except sqlite3.OperationalError:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    if attempt == _TXN_RETRY_ATTEMPTS - 1:
                        raise
                    time.sleep(_TXN_RETRY_BASE_DELAY_S * (2 ** attempt) + random.uniform(0, _TXN_RETRY_BASE_DELAY_S))
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
        self._migrate_rename_collection_tenants(conn)
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

            CREATE TABLE IF NOT EXISTS notifications (
              id            BLOB(16) PRIMARY KEY,
              user_id       BLOB(16) DEFAULT NULL,
              type          TEXT NOT NULL,
              title         TEXT NOT NULL,
              body          TEXT,
              link          TEXT,
              ref_type      TEXT,
              ref_id        TEXT,
              data_json     TEXT,
              created_at    INTEGER NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notification_reads (
              notification_id BLOB(16) NOT NULL,
              user_id          BLOB(16) NOT NULL,
              read_at          INTEGER NOT NULL,
              PRIMARY KEY (notification_id, user_id),
              FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tenant_join_requests (
              id                            BLOB(16) PRIMARY KEY,
              user_id                       BLOB(16) NOT NULL,
              org_id                        INTEGER NOT NULL,
              status                        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
              message                       TEXT,
              reviewed_by                   BLOB(16),
              review_reason                 TEXT,
              granted_tenant_role           TEXT,
              granted_classification_level  INTEGER,
              created_at                    INTEGER NOT NULL,
              resolved_at                   INTEGER,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
              FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tenant_share_requests (
              id                  BLOB(16) PRIMARY KEY,
              requesting_org_id   INTEGER NOT NULL,
              target_org_id       INTEGER NOT NULL,
              status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
              message             TEXT,
              requested_by        BLOB(16) NOT NULL,
              reviewed_by         BLOB(16),
              review_reason       TEXT,
              created_at          INTEGER NOT NULL,
              resolved_at         INTEGER,
              FOREIGN KEY (requesting_org_id) REFERENCES organizations(id) ON DELETE CASCADE,
              FOREIGN KEY (target_org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tenant_share_grants (
              request_id          BLOB(16) NOT NULL,
              collection_id       TEXT NOT NULL,
              max_classification  INTEGER,
              PRIMARY KEY (request_id, collection_id),
              FOREIGN KEY (request_id) REFERENCES tenant_share_requests(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tenant_invitations (
              id            BLOB(16) PRIMARY KEY,
              org_id        INTEGER NOT NULL,
              user_id       BLOB(16) NOT NULL,
              invited_by    BLOB(16) NOT NULL,
              status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','declined','cancelled')),
              message       TEXT,
              created_at    INTEGER NOT NULL,
              resolved_at   INTEGER,
              FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_user_orgs ON user_orgs(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_roles ON user_roles(user_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(c_id, created_at, id);
            CREATE INDEX IF NOT EXISTS idx_tenant_collections ON tenant_collections(org_id);
            CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_notification_reads_user ON notification_reads(user_id);
            CREATE INDEX IF NOT EXISTS idx_join_requests_org ON tenant_join_requests(org_id, status);
            CREATE INDEX IF NOT EXISTS idx_join_requests_user ON tenant_join_requests(user_id);
            CREATE INDEX IF NOT EXISTS idx_share_requests_target ON tenant_share_requests(target_org_id, status);
            CREATE INDEX IF NOT EXISTS idx_share_requests_requesting ON tenant_share_requests(requesting_org_id);
            CREATE INDEX IF NOT EXISTS idx_invitations_org ON tenant_invitations(org_id, status);
            CREATE INDEX IF NOT EXISTS idx_invitations_user ON tenant_invitations(user_id, status);

            CREATE TABLE IF NOT EXISTS revoked_tokens (
              jti           TEXT PRIMARY KEY,
              revoked_at    INTEGER NOT NULL
            );

            -- Backstops file_join_request/invite_user/file_share_request's
            -- check-then-insert against a concurrent double-submit (the
            -- check itself runs outside any transaction, so it can't close
            -- this race on its own) -- a second pending request for the
            -- same pair now fails fast with IntegrityError instead of
            -- silently creating a duplicate.
            CREATE UNIQUE INDEX IF NOT EXISTS idx_join_requests_one_pending
              ON tenant_join_requests(user_id, org_id) WHERE status = 'pending';
            CREATE UNIQUE INDEX IF NOT EXISTS idx_invitations_one_pending
              ON tenant_invitations(user_id, org_id) WHERE status = 'pending';
            CREATE UNIQUE INDEX IF NOT EXISTS idx_share_requests_one_pending
              ON tenant_share_requests(requesting_org_id, target_org_id) WHERE status = 'pending';
            """
        )
        # executescript commits implicitly; run ADD-COLUMN migrations separately
        self._migrate_add_columns(conn)

    def _migrate_rename_collection_tenants(self, conn: sqlite3.Connection) -> None:
        """One-time migration from this feature's earlier table name
        (collection_tenants) to the current one (tenant_collections). Must
        run BEFORE the `CREATE TABLE IF NOT EXISTS tenant_collections` in
        `initialize()` -- that statement would otherwise silently create a
        new, empty tenant_collections table first (since collection_tenants
        doesn't match that name), and the rename would then fail because its
        target already exists, orphaning the old table's data under its old
        name instead of migrating it. No-op if collection_tenants doesn't
        exist, or tenant_collections already does (already migrated, or a
        fresh install that never had the old name)."""
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "collection_tenants" in tables and "tenant_collections" not in tables:
            conn.execute("ALTER TABLE collection_tenants RENAME TO tenant_collections")
            conn.commit()

    def _migrate_add_columns(self, conn: sqlite3.Connection) -> None:
        """Guarded, idempotent ADD COLUMN migrations. Each checks the target
        column via PRAGMA table_info before altering, rather than relying on
        a blanket try/except to tell "already migrated" apart from a genuine
        failure -- the latter used to be silently swallowed too."""

        def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
            cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            if column not in cols:
                conn.execute(ddl)
                conn.commit()

        _add_column_if_missing("user_orgs", "classification_level",
                                "ALTER TABLE user_orgs ADD COLUMN classification_level INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing("user_orgs", "tenant_role",
                                "ALTER TABLE user_orgs ADD COLUMN tenant_role TEXT DEFAULT NULL")
        _add_column_if_missing("tenant_collections", "role",
                                "ALTER TABLE tenant_collections ADD COLUMN role TEXT NOT NULL DEFAULT 'access'")
        _add_column_if_missing("tenant_collections", "max_classification",
                                "ALTER TABLE tenant_collections ADD COLUMN max_classification INTEGER DEFAULT NULL")
        _add_column_if_missing("users", "last_login_at",
                                "ALTER TABLE users ADD COLUMN last_login_at INTEGER DEFAULT NULL")
        _add_column_if_missing("users", "last_seen_at",
                                "ALTER TABLE users ADD COLUMN last_seen_at INTEGER DEFAULT NULL")

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

    @with_txn
    def revoke_token(self, conn, *, jti: str, ts: int):
        conn.execute("INSERT OR IGNORE INTO revoked_tokens (jti, revoked_at) VALUES (?, ?)", (jti, ts))

    def is_token_revoked(self, jti: str) -> bool:
        return self._get_conn().execute(
            "SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,)
        ).fetchone() is not None

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
    def insert_organization(self, conn, *, name: str, abbreviation: str, created_ts: int) -> bool:
        """Returns False if a tenant with this name or abbreviation already
        exists (the INSERT OR IGNORE silently no-ops) -- without this, a
        caller has no way to tell "created" apart from "already existed,
        nothing happened", which used to look identical from the outside."""
        cur = conn.execute("INSERT OR IGNORE INTO organizations (name, abbreviation, created_at) VALUES (?, ?, ?)",
                            (name, abbreviation, created_ts))
        return cur.rowcount > 0

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

    def get_organization_by_id(self, id: int) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, name, abbreviation, created_at FROM organizations WHERE id = ?", (id,)
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

    def get_org_moderators(self, org_id: int) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT user_id FROM user_orgs WHERE org_id = ? AND tenant_role IN ('moderator', 'co-moderator')",
            (org_id,)
        ).fetchall()

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

    # ---- notifications ----

    @with_txn
    def insert_notification(self, conn, *, notif_id: uuid.UUID, user_id: uuid.UUID | None, type: str,
                            title: str, body: str | None, link: str | None, ref_type: str | None,
                            ref_id: str | None, data_json: str | None, ts: int):
        conn.execute(
            "INSERT INTO notifications (id, user_id, type, title, body, link, ref_type, ref_id, data_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (notif_id.bytes, user_id.bytes if user_id else None, type, title, body, link,
             ref_type, ref_id, data_json, ts),
        )

    # A broadcast (user_id IS NULL) is only visible to a user if it was sent
    # on or after that user's account was created -- otherwise every new
    # signup would inherit the entire history of past announcements.
    _VISIBLE_BROADCAST = (
        "(n.user_id = ? OR (n.user_id IS NULL AND n.created_at >= (SELECT created_at FROM users WHERE id = ?)))"
    )

    def get_notifications_for_user(
        self, user_id: uuid.UUID, limit: int,
        before_created_at: int | None = None, before_rowid: int | None = None,
    ) -> list[sqlite3.Row]:
        cursor_clause = ""
        params: list = [user_id.bytes, user_id.bytes, user_id.bytes]
        if before_created_at is not None:
            cursor_clause = "AND (n.created_at < ? OR (n.created_at = ? AND n.rowid < ?))"
            params += [before_created_at, before_created_at, before_rowid]
        params.append(limit)
        return self._get_conn().execute(
            f"SELECT n.id, n.user_id, n.type, n.title, n.body, n.link, n.ref_type, n.ref_id, n.data_json, "
            f"n.created_at, n.rowid, (nr.read_at IS NOT NULL) AS is_read "
            f"FROM notifications n "
            f"LEFT JOIN notification_reads nr ON nr.notification_id = n.id AND nr.user_id = ? "
            f"WHERE {self._VISIBLE_BROADCAST} {cursor_clause} "
            f"ORDER BY n.created_at DESC, n.rowid DESC LIMIT ?",
            params,
        ).fetchall()

    def list_broadcast_notifications(
        self, limit: int, before_created_at: int | None = None, before_rowid: int | None = None,
    ) -> list[sqlite3.Row]:
        """Admin-facing broadcast history -- unlike get_notifications_for_user,
        this is not scoped to a viewer and returns every broadcast ever sent
        (user_id IS NULL), not the mixed per-user inbox."""
        cursor_clause = ""
        params: list = []
        if before_created_at is not None:
            cursor_clause = "AND (created_at < ? OR (created_at = ? AND rowid < ?))"
            params += [before_created_at, before_created_at, before_rowid]
        params.append(limit)
        return self._get_conn().execute(
            f"SELECT id, title, body, link, created_at, rowid FROM notifications "
            f"WHERE user_id IS NULL {cursor_clause} "
            f"ORDER BY created_at DESC, rowid DESC LIMIT ?",
            params,
        ).fetchall()

    def get_unread_notification_count(self, user_id: uuid.UUID) -> int:
        row = self._get_conn().execute(
            f"SELECT COUNT(*) AS c FROM notifications n "
            f"LEFT JOIN notification_reads nr ON nr.notification_id = n.id AND nr.user_id = ? "
            f"WHERE {self._VISIBLE_BROADCAST} AND nr.read_at IS NULL",
            (user_id.bytes, user_id.bytes, user_id.bytes),
        ).fetchone()
        return row["c"] if row else 0

    @with_txn
    def mark_notification_read(self, conn, *, notification_id: uuid.UUID, user_id: uuid.UUID, ts: int):
        conn.execute(
            "INSERT OR IGNORE INTO notification_reads (notification_id, user_id, read_at) VALUES (?, ?, ?)",
            (notification_id.bytes, user_id.bytes, ts),
        )

    @with_txn
    def mark_all_notifications_read(self, conn, *, user_id: uuid.UUID, ts: int):
        conn.execute(
            f"INSERT OR IGNORE INTO notification_reads (notification_id, user_id, read_at) "
            f"SELECT n.id, ?, ? FROM notifications n "
            f"WHERE {self._VISIBLE_BROADCAST}",
            (user_id.bytes, ts, user_id.bytes, user_id.bytes),
        )

    # ---- tenant join requests ----

    @with_txn
    def insert_join_request(self, conn, *, req_id: uuid.UUID, user_id: uuid.UUID, org_id: int,
                            message: str | None, ts: int):
        conn.execute(
            "INSERT INTO tenant_join_requests (id, user_id, org_id, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (req_id.bytes, user_id.bytes, org_id, message, ts),
        )

    def get_join_request(self, req_id: uuid.UUID) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, user_id, org_id, status, message, reviewed_by, review_reason, "
            "granted_tenant_role, granted_classification_level, created_at, resolved_at "
            "FROM tenant_join_requests WHERE id = ?",
            (req_id.bytes,),
        ).fetchone()

    def get_pending_join_request(self, user_id: uuid.UUID, org_id: int) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id FROM tenant_join_requests WHERE user_id = ? AND org_id = ? AND status = 'pending'",
            (user_id.bytes, org_id),
        ).fetchone()

    def list_join_requests_for_org(self, org_id: int, status: str | None = None) -> list[sqlite3.Row]:
        if status:
            return self._get_conn().execute(
                "SELECT jr.id, jr.user_id, jr.org_id, jr.status, jr.message, jr.reviewed_by, jr.review_reason, "
                "jr.granted_tenant_role, jr.granted_classification_level, jr.created_at, jr.resolved_at, "
                "u.username, u.first_name, u.last_name, u.email "
                "FROM tenant_join_requests jr JOIN users u ON u.id = jr.user_id "
                "WHERE jr.org_id = ? AND jr.status = ? ORDER BY jr.created_at DESC",
                (org_id, status),
            ).fetchall()
        return self._get_conn().execute(
            "SELECT jr.id, jr.user_id, jr.org_id, jr.status, jr.message, jr.reviewed_by, jr.review_reason, "
            "jr.granted_tenant_role, jr.granted_classification_level, jr.created_at, jr.resolved_at, "
            "u.username, u.first_name, u.last_name, u.email "
            "FROM tenant_join_requests jr JOIN users u ON u.id = jr.user_id "
            "WHERE jr.org_id = ? ORDER BY jr.created_at DESC",
            (org_id,),
        ).fetchall()

    def list_join_requests_for_user(self, user_id: uuid.UUID) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT jr.id, jr.user_id, jr.org_id, jr.status, jr.message, jr.reviewed_by, jr.review_reason, "
            "jr.granted_tenant_role, jr.granted_classification_level, jr.created_at, jr.resolved_at, "
            "o.name AS org_name, o.abbreviation AS org_abbreviation "
            "FROM tenant_join_requests jr JOIN organizations o ON o.id = jr.org_id "
            "WHERE jr.user_id = ? ORDER BY jr.created_at DESC",
            (user_id.bytes,),
        ).fetchall()

    @with_txn
    def resolve_join_request(self, conn, *, req_id: uuid.UUID, status: str, reviewed_by: uuid.UUID,
                             review_reason: str | None, granted_tenant_role: str | None,
                             granted_classification_level: int | None, ts: int) -> bool:
        """Returns False (no-op) if the request was already resolved by a
        concurrent call -- the WHERE clause is the authoritative guard
        against double-resolution, not the caller's earlier read."""
        cur = conn.execute(
            "UPDATE tenant_join_requests SET status = ?, reviewed_by = ?, review_reason = ?, "
            "granted_tenant_role = ?, granted_classification_level = ?, resolved_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (status, reviewed_by.bytes, review_reason, granted_tenant_role,
             granted_classification_level, ts, req_id.bytes),
        )
        return cur.rowcount > 0

    @with_txn
    def approve_join_request_and_grant(self, conn, *, req_id: uuid.UUID, user_id: uuid.UUID, org_id: int,
                                       classification_level: int, tenant_role: str | None,
                                       reviewer_id: uuid.UUID, ts: int) -> bool:
        """Resolves the join request and grants tenant membership in one
        transaction. The status UPDATE below runs first and is the
        authoritative guard against a concurrent approve/reject of the same
        request (its WHERE clause only matches a still-pending row); the
        one-moderator-per-tenant check runs against this same connection,
        inside this same transaction, so two concurrent moderator-grants for
        the same tenant can no longer both succeed -- returns False if the
        request was already resolved, raises ModeratorConflictError if
        granting would create a second moderator (both cases roll back
        cleanly via with_txn)."""
        cur = conn.execute(
            "UPDATE tenant_join_requests SET status = 'approved', reviewed_by = ?, review_reason = NULL, "
            "granted_tenant_role = ?, granted_classification_level = ?, resolved_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (reviewer_id.bytes, tenant_role, classification_level, ts, req_id.bytes),
        )
        if cur.rowcount == 0:
            return False

        if tenant_role == "moderator":
            existing = conn.execute(
                "SELECT user_id FROM user_orgs WHERE org_id = ? AND tenant_role = 'moderator'",
                (org_id,),
            ).fetchone()
            if existing and bytes(existing["user_id"]) != user_id.bytes:
                raise ModeratorConflictError("Tenant already has a moderator.")

        conn.execute("INSERT OR IGNORE INTO user_orgs (user_id, org_id) VALUES (?, ?)", (user_id.bytes, org_id))
        conn.execute("UPDATE user_orgs SET classification_level = ? WHERE user_id = ? AND org_id = ?",
                     (classification_level, user_id.bytes, org_id))
        if tenant_role:
            conn.execute("UPDATE user_orgs SET tenant_role = ? WHERE user_id = ? AND org_id = ?",
                         (tenant_role, user_id.bytes, org_id))
        return True

    # ---- tenant share requests ----

    @with_txn
    def insert_share_request(self, conn, *, req_id: uuid.UUID, requesting_org_id: int, target_org_id: int,
                             message: str | None, requested_by: uuid.UUID, ts: int):
        conn.execute(
            "INSERT INTO tenant_share_requests (id, requesting_org_id, target_org_id, message, requested_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (req_id.bytes, requesting_org_id, target_org_id, message, requested_by.bytes, ts),
        )

    def get_share_request(self, req_id: uuid.UUID) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, requesting_org_id, target_org_id, status, message, requested_by, reviewed_by, "
            "review_reason, created_at, resolved_at FROM tenant_share_requests WHERE id = ?",
            (req_id.bytes,),
        ).fetchone()

    def list_share_requests_for_org(self, org_id: int, direction: str, status: str | None = None) -> list[sqlite3.Row]:
        org_col = "target_org_id" if direction == "incoming" else "requesting_org_id"
        other_col = "requesting_org_id" if direction == "incoming" else "target_org_id"
        query = (
            f"SELECT sr.id, sr.requesting_org_id, sr.target_org_id, sr.status, sr.message, sr.requested_by, "
            f"sr.reviewed_by, sr.review_reason, sr.created_at, sr.resolved_at, "
            f"o.name AS other_org_name, o.abbreviation AS other_org_abbreviation "
            f"FROM tenant_share_requests sr JOIN organizations o ON o.id = sr.{other_col} "
            f"WHERE sr.{org_col} = ?"
        )
        params: list = [org_id]
        if status:
            query += " AND sr.status = ?"
            params.append(status)
        query += " ORDER BY sr.created_at DESC"
        return self._get_conn().execute(query, params).fetchall()

    @with_txn
    def resolve_share_request(self, conn, *, req_id: uuid.UUID, status: str, reviewed_by: uuid.UUID,
                              review_reason: str | None, ts: int) -> bool:
        """Returns False (no-op) if the request was already resolved by a
        concurrent call."""
        cur = conn.execute(
            "UPDATE tenant_share_requests SET status = ?, reviewed_by = ?, review_reason = ?, resolved_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (status, reviewed_by.bytes, review_reason, ts, req_id.bytes),
        )
        return cur.rowcount > 0

    @with_txn
    def approve_share_request_and_grant(
        self, conn, *, req_id: uuid.UUID, requesting_org_id: int,
        grants: list[tuple[str, int | None]], reviewer_id: uuid.UUID, ts: int,
    ) -> bool:
        """Resolves the share request and grants every approved collection in
        one transaction. The status UPDATE runs first and is the
        authoritative guard against a concurrent approve/reject of the same
        request -- returns False without granting anything if it was already
        resolved."""
        cur = conn.execute(
            "UPDATE tenant_share_requests SET status = 'approved', reviewed_by = ?, review_reason = NULL, "
            "resolved_at = ? WHERE id = ? AND status = 'pending'",
            (reviewer_id.bytes, ts, req_id.bytes),
        )
        if cur.rowcount == 0:
            return False

        for collection_id, max_classification in grants:
            conn.execute(
                "INSERT OR REPLACE INTO tenant_collections (collection_id, org_id, role, max_classification) "
                "VALUES (?, ?, 'access', ?)",
                (collection_id, requesting_org_id, max_classification),
            )
            conn.execute(
                "INSERT OR REPLACE INTO tenant_share_grants (request_id, collection_id, max_classification) "
                "VALUES (?, ?, ?)",
                (req_id.bytes, collection_id, max_classification),
            )
        return True

    @with_txn
    def insert_share_grant(self, conn, *, req_id: uuid.UUID, collection_id: str, max_classification: int | None):
        conn.execute(
            "INSERT OR REPLACE INTO tenant_share_grants (request_id, collection_id, max_classification) "
            "VALUES (?, ?, ?)",
            (req_id.bytes, collection_id, max_classification),
        )

    def list_share_grants(self, req_id: uuid.UUID) -> list[sqlite3.Row]:
        return self._get_conn().execute(
            "SELECT collection_id, max_classification FROM tenant_share_grants WHERE request_id = ?",
            (req_id.bytes,),
        ).fetchall()

    # ---- tenant invitations ----

    @with_txn
    def insert_invitation(self, conn, *, inv_id: uuid.UUID, org_id: int, user_id: uuid.UUID,
                          invited_by: uuid.UUID, message: str | None, ts: int):
        conn.execute(
            "INSERT INTO tenant_invitations (id, org_id, user_id, invited_by, message, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (inv_id.bytes, org_id, user_id.bytes, invited_by.bytes, message, ts),
        )

    def get_invitation(self, inv_id: uuid.UUID) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id, org_id, user_id, invited_by, status, message, created_at, resolved_at "
            "FROM tenant_invitations WHERE id = ?",
            (inv_id.bytes,),
        ).fetchone()

    def get_pending_invitation(self, user_id: uuid.UUID, org_id: int) -> sqlite3.Row | None:
        return self._get_conn().execute(
            "SELECT id FROM tenant_invitations WHERE user_id = ? AND org_id = ? AND status = 'pending'",
            (user_id.bytes, org_id),
        ).fetchone()

    def list_invitations_for_org(self, org_id: int, status: str | None = None) -> list[sqlite3.Row]:
        query = (
            "SELECT inv.id, inv.org_id, inv.user_id, inv.invited_by, inv.status, inv.message, "
            "inv.created_at, inv.resolved_at, u.username, u.email, u.first_name, u.last_name "
            "FROM tenant_invitations inv JOIN users u ON u.id = inv.user_id "
            "WHERE inv.org_id = ?"
        )
        params: list = [org_id]
        if status:
            query += " AND inv.status = ?"
            params.append(status)
        query += " ORDER BY inv.created_at DESC"
        return self._get_conn().execute(query, params).fetchall()

    def list_invitations_for_user(self, user_id: uuid.UUID, status: str | None = None) -> list[sqlite3.Row]:
        query = (
            "SELECT inv.id, inv.org_id, inv.user_id, inv.invited_by, inv.status, inv.message, "
            "inv.created_at, inv.resolved_at, o.name AS org_name, o.abbreviation AS org_abbreviation "
            "FROM tenant_invitations inv JOIN organizations o ON o.id = inv.org_id "
            "WHERE inv.user_id = ?"
        )
        params: list = [user_id.bytes]
        if status:
            query += " AND inv.status = ?"
            params.append(status)
        query += " ORDER BY inv.created_at DESC"
        return self._get_conn().execute(query, params).fetchall()

    @with_txn
    def resolve_invitation(self, conn, *, inv_id: uuid.UUID, status: str, ts: int) -> bool:
        """Returns False (no-op) if the invitation was already resolved by a
        concurrent call -- e.g. an admin cancelling at the same moment the
        invited user accepts."""
        cur = conn.execute(
            "UPDATE tenant_invitations SET status = ?, resolved_at = ? WHERE id = ? AND status = 'pending'",
            (status, ts, inv_id.bytes),
        )
        return cur.rowcount > 0

    @with_txn
    def accept_invitation_and_grant(self, conn, *, inv_id: uuid.UUID, user_id: uuid.UUID, org_id: int, ts: int) -> bool:
        """Resolves the invitation and grants tenant membership in one
        transaction. The status UPDATE runs first and is the authoritative
        guard against a concurrent cancel/decline of the same invitation --
        returns False without granting membership if it was already
        resolved."""
        cur = conn.execute(
            "UPDATE tenant_invitations SET status = 'accepted', resolved_at = ? WHERE id = ? AND status = 'pending'",
            (ts, inv_id.bytes),
        )
        if cur.rowcount == 0:
            return False

        conn.execute("INSERT OR IGNORE INTO user_orgs (user_id, org_id) VALUES (?, ?)", (user_id.bytes, org_id))
        conn.execute("UPDATE user_orgs SET classification_level = 0 WHERE user_id = ? AND org_id = ?",
                     (user_id.bytes, org_id))
        return True

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
