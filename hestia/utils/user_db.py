import sqlite3
import threading

BUSY_TIMEOUT_MS = 5000

def create_sqlite_connection(db_path: str) -> tuple[callable, callable]:
    _local = threading.local()
    _lock = threading.Lock()

    def get_conn() -> sqlite3.Connection:
        """
        Create a thread-local connection in non-autocommit mode (isolation_level='DEFERRED').
        This lets us use BEGIN/COMMIT/ROLLBACK reliably.
        """
        conn = getattr(_local, "conn", None)
        if conn is None:
            # Use default isolation_level='DEFERRED'.
            conn = sqlite3.connect(db_path, check_same_thread=False)  # NOT autocommit
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

            CREATE TABLE IF NOT EXISTS permissions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                description         TEXT
            );

            CREATE TABLE IF NOT EXISTS role_hierarchy (
                role_id             INTEGER NOT NULL,
                parent_id           INTEGER NOT NULL,
                PRIMARY KEY(role_id, parent_id),
                FOREIGN KEY(role_id)   REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_id) REFERENCES roles(id) ON DELETE CASCADE
            );

            -- map users to organizations.
            CREATE TABLE IF NOT EXISTS user_orgs (
                user_id             BLOB(16) NOT NULL,
                org_id              INTEGER NOT NULL,
                PRIMARY KEY         (user_id, org_id),
                FOREIGN KEY         (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY         (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );

            -- map users to roles.
            CREATE TABLE IF NOT EXISTS user_roles(
                user_id             BLOB(16) NOT NULL,
                role_id             INTEGER NOT NULL,
                starts_at           INTEGER NOT NULL,
                expires_at          INTEGER DEFAULT NULL,
                PRIMARY KEY         (user_id, role_id),
                FOREIGN KEY         (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY         (role_id) REFERENCES roles(id) ON DELETE CASCADE
            );

            -- role permissions mapping
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id             INTEGER NOT NULL,
                permission_id       INTEGER NOT NULL,
                value               TEXT,
                PRIMARY KEY         (role_id, permission_id),
                FOREIGN KEY         (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY         (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            );

            -- user permissions mapping, allow to override role permissions
            CREATE TABLE IF NOT EXISTS user_permissions(
                user_id             BLOB(16) NOT NULL,
                permission_id       INTEGER NOT NULL,
                value               TEXT,
                starts_at           INTEGER NOT NULL,
                expires_at          INTEGER DEFAULT NULL,
                PRIMARY KEY         (user_id, permission_id),
                FOREIGN KEY         (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY         (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            );

            -- default global role definition
            INSERT OR IGNORE INTO roles (name, description) VALUES
                ('admin', 'Full system access'),
                ('moderator', 'Access to content management features'),
                ('user', 'Access to general system features'),
                ('guest', 'Only chat access' );

            -- default global role hierarchy
            INSERT OR IGNORE INTO role_hierarchy (role_id, parent_id) VALUES
                ((SELECT id FROM roles WHERE name='user'),
                (SELECT id FROM roles WHERE name='guest')),

                ((SELECT id FROM roles WHERE name='moderator'),
                (SELECT id FROM roles WHERE name='user')),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM roles WHERE name='moderator'));

            -- map users to conversations
            CREATE TABLE IF NOT EXISTS conversations (
              id                    BLOB(16) PRIMARY KEY,
              user_id               BLOB(16) NOT NULL,
              title                 TEXT,
              metadata_json         TEXT,
              created_at            INTEGER NOT NULL,
              updated_at            INTEGER NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            -- map messages to conversations
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
            CREATE INDEX IF NOT EXISTS idx_role_permissions ON role_permissions(role_id);
            CREATE INDEX IF NOT EXISTS idx_user_permissions ON user_permissions(user_id);
            """
        )

    # User management
    def list_users(self) -> list[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, username, email, first_name, last_name, must_change_pw, created_at, updated_at, expires_at
            FROM users
            ORDER BY last_name ASC
            """
        ).fetchall()
    
    @with_txn
    def insert_user(
        self, 
        conn: sqlite3.Connection,
        *, 
        user_id: bytes,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        auth_source: str,   # "ldap" or "local"
        password_hash: bytes,
        salt: bytes,
        must_change_pw: int,
        created_ts: int,
        expires_ts: int | None = None):

        conn.execute(
            """
            INSERT INTO users (id, username, email, first_name, last_name, auth_source,
            password_hash, salt, must_change_pw, created_at, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, email, first_name, last_name, auth_source,
             password_hash, salt, must_change_pw, created_ts, created_ts, expires_ts),
        )

    @with_txn
    def delete_user(self, conn: sqlite3.Connection, *, id: bytes):
        conn.execute("DELETE FROM users WHERE id = ?", (id,))

    @with_txn
    def set_must_change_pw(self, conn:sqlite3.Connection, *, change: int, id: bytes, updated_ts: int):
        conn.execute(
            "UPDATE users SET must_change_pw = ?, updated_at = ? WHERE id = ?",
            (change, updated_ts, id)
        )

    @with_txn
    def set_user_expiration(self, conn: sqlite3.Connection, *, id: bytes, expires_ts: int, updated_ts: int):
        conn.execute(
            """
            UPDATE users SET expires_at = ?, updated_at = ? WHERE id = ?
            """,
            (expires_ts, updated_ts, id)
        )
    
    @with_txn
    def update_username(self, conn: sqlite3.Connection, *, id: bytes, new_username: str, updated_ts: int):
        conn.execute(
            """
            UPDATE users SET username = ?, updated_at = ? WHERE id = ?
            """,
            (new_username, updated_ts, id)
        )

    @with_txn
    def update_user_email(self, conn: sqlite3.Connection, *, id: bytes, new_email: str, updated_ts: int):
        conn.execute(
            """
            UPDATE users SET email = ?, updated_at = ? WHERE id = ?
            """,
            (new_email, updated_ts, id)
        )

    @with_txn
    def update_user_first_name(self, conn: sqlite3.Connection, *, id: bytes, new_name: str, updated_ts: int):
        conn.execute(
            """
            UPDATE users SET first_name = ?, updated_at = ? 
            WHERE id = ?
            """,
            (new_name, updated_ts, id)
        )
    
    @with_txn
    def update_user_last_name(self, conn: sqlite3.Connection, *, id: bytes, new_name: str, updated_ts: int):
        conn.execute(
            """
            UPDATE users SET last_name = ?, updated_at = ? 
            WHERE id = ?
            """,
            (new_name, updated_ts, id)
        )
    
    @with_txn
    def update_user_password(
        self, 
        conn: sqlite3.Connection,
        *, 
        id: bytes,
        new_hash: bytes,
        new_salt: bytes,
        updated_ts: int):

        conn.execute(
            """
            UPDATE users SET password_hash = ?, salt = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_hash, new_salt, updated_ts, id),
        )

    @with_txn
    def add_user_to_organization(self, conn: sqlite3.Connection, *, user_id: bytes, org_id: int):
        conn.execute(
            """
            INSERT OR IGNORE INTO user_orgs (user_id, org_id) VALUES (?, ?)
            """,
            (user_id, org_id)
        )

    @with_txn
    def remove_user_from_organization(self, conn: sqlite3.Connection, *, user_id: bytes, org_id: int):
        conn.execute("DELETE FROM user_orgs WHERE user_id = ? AND org_id = ?", (user_id, org_id))

    @with_txn
    def add_role_to_user(
        self, 
        conn: sqlite3.Connection, 
        *,
        user_id: bytes, 
        role_id: int,
        starts_ts: int,
        expires_ts: int | None = None):
        conn.execute(
            """
            INSERT INTO user_roles (user_id, role_id, starts_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role_id, starts_ts, expires_ts)
        )
    
    @with_txn
    def remove_role_from_user(self, conn: sqlite3.Connection, *, user_id: bytes, role_id: int):
        conn.execute("DELETE FROM user_roles WHERE user_id = ? AND role_id = ?", (user_id, role_id))

    @with_txn
    def set_user_permission(
        self, 
        conn: sqlite3.Connection, 
        *, 
        user_id: bytes, 
        permission_id: int, 
        value: str,
        starts_ts: int,
        expires_ts: int | None = None):
        """
        Assigns or updates a single permission value for a user.
        Stores into user_permissions(user_id, permission_id, value, expires_at).
        """
        conn.execute(
            """
            INSERT INTO user_permissions (user_id, permission_id, value, starts_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, permission_id)
            DO UPDATE SET value = excluded.value
            """,
            (user_id, permission_id, value, starts_ts, expires_ts)
        )

    @with_txn
    def delete_user_permission(self, conn: sqlite3.Connection, *, user_id: bytes, permission_id: int):
        conn.execute("DELETE FROM user_permissions WHERE user_id = ? AND permission_id = ?", (user_id, permission_id))

    def get_user_by_id(self, id: bytes) -> sqlite3.Row:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, username, email, first_name, last_name,
                password_hash, salt, auth_source, must_change_pw, 
                created_at, updated_at, expires_at
            FROM users WHERE id = ?
            """,
            (id,),
        ).fetchone()

    def get_user_by_username(self, username: str) -> sqlite3.Row:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, username, email, first_name, last_name,
                password_hash, salt, auth_source, must_change_pw, 
                created_at, updated_at, expires_at
            FROM users WHERE username = ?
            """,
            (username,),
        ).fetchone()
    
    def get_user_by_email(self, email: str) -> sqlite3.Row:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, username, email, first_name, last_name,
                password_hash, salt, auth_source, must_change_pw, 
                created_at, updated_at, expires_at
            FROM users WHERE email = ?
            """,
            (email,),
        ).fetchone()

    def get_user_for_login(self, identifier: str) -> sqlite3.Row:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, username, email, first_name, last_name,
                password_hash, salt, auth_source, must_change_pw, 
                created_at, updated_at, expires_at
            FROM users 
            WHERE username = ? OR email = ?
            """,
            (identifier, identifier),
        ).fetchone()

    def get_user_roles(self, id: bytes) -> list[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT r.id, r.name, r.description, ur.starts_at, ur.expires_at
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = ? 
            """,
            (id,)
        ).fetchall()

    def get_user_organizations(self, id: bytes) -> list[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT o.id, o.name, o.abbreviation, o.created_at
            FROM user_orgs uo
            JOIN organizations o ON uo.org_id = o.id
            WHERE uo.user_id = ?
            """,
            (id,)
        ).fetchall()

    def get_user_permissions(self, id: bytes) -> list[sqlite3.Row]:
        """
        Returns only user-specific permissions stored in user_permissions.
        """
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT p.id, p.name, up.value, up.starts_at, up.expires_at
            FROM user_permissions up
            JOIN permissions p ON up.permission_id = p.id
            WHERE up.user_id = ?            
            """,
            (id,)
        ).fetchall()

    # organization
    @with_txn
    def insert_organization(self, conn: sqlite3.Connection, *, name: str, abbreviation: str, created_ts):
        conn.execute(
            """
            INSERT OR IGNORE INTO organizations (name, abbreviation, created_at) VALUES (?, ?, ?)            
            """,
            (name, abbreviation, created_ts)
        )
    
    @with_txn
    def update_organization(self, conn: sqlite3.Connection, *, id: int, name: str, abbreviation: str):
        conn.execute(
            """
            UPDATE organizations
            SET name = ?, abbreviation = ?
            WHERE id = ?
            """,
            (name, abbreviation, id)
        )

    @with_txn
    def delete_organization(self, conn: sqlite3.Connection, *, id: int):
        conn.execute("DELETE FROM organizations WHERE id = ?", (id,))

    def get_organization_by_id(self, id: int):
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, name, abbreviation, created_at FROM organizations
            WHERE id = ?
            """,
            (id,)
        ).fetchone()
    
    def get_organization_by_name(self, name: str):
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, name, abbreviation, created_at FROM organizations
            WHERE name = ?
            """,
            (name,)
        ).fetchone()
    
    def get_organization_users(self, id: int) -> list[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT u.id, u.username, u.email, u.first_name, u.last_name
            FROM user_orgs uo
            JOIN users u ON uo.user_id = u.id
            WHERE uo.org_id = ?
            """,
            (id,)
        ).fetchall()

    def list_organizations(self):
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, name, abbreviation, created_at FROM organizations
            """
        ).fetchall()


    # role management
    @with_txn
    def insert_role(self, conn: sqlite3.Connection, *, name: str, description: str):
        conn.execute(
            """
            INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)
            """,
            (name, description)
        )

    @with_txn
    def update_role(self, conn: sqlite3.Connection, *, id: int, name: str, description: str):
        conn.execute(
            """
            UPDATE roles SET name = ?, description = ?
            WHERE id = ?
            """,
            (name, description, id)
        )

    @with_txn
    def delete_role(self, conn: sqlite3.Connection, *, id: int):
        conn.execute("DELETE FROM roles WHERE id = ?", (id,))

    @with_txn
    def add_role_parent(self, conn: sqlite3.Connection, *, role_id: int, parent_id: int):
        conn.execute(
            """
            INSERT OR IGNORE INTO role_hierarchy (role_id, parent_id)
            VALUES (?, ?)
            """, 
            (role_id, parent_id)
        )

    @with_txn
    def remove_role_parent(self, conn: sqlite3.Connection, *, role_id: int, parent_id: int):
        conn.execute(
            """
            DELETE FROM role_hierarchy
            WHERE role_id = ? AND parent_id = ?
            """, 
            (role_id, parent_id)
        )

    @with_txn
    def set_role_permission(
        self, 
        conn: sqlite3.Connection,
        *, 
        role_id: int,
        permission_id: int,
        value: str | None
        ):
        """
        Assigns or updates a single permission value for a role.
        Stores into role_permissions(role_id, permission_id, value).
        """
        conn.execute(
            """
            INSERT INTO role_permissions (role_id, permission_id, value)
            VALUES (?, ?, ?)
            ON CONFLICT(role_id, permission_id)
            DO UPDATE SET value = excluded.value
            """,
            (role_id, permission_id, value),
        )
        
    @with_txn
    def delete_role_permission(self, conn: sqlite3.Connection, *, role_id: int, permission_id: int):
        conn.execute(
            """
            DELETE FROM role_permissions
            WHERE role_id = ? AND permission_id = ?
            """,
            (role_id, permission_id)
        )

    def get_role_by_name(self, role: str) -> sqlite3.Row | None:
        conn = self._get_conn()
        return conn.execute(
            "SELECT id, name, description FROM roles WHERE name = ?",
            (role,)
        ).fetchone()
 
    def get_role_by_id(self, id: int) -> sqlite3.Row | None:
        conn = self._get_conn()
        return conn.execute("SELECT id, name, description FROM roles WHERE id = ?", (id,)).fetchone()
    
    def get_parent_roles(self, id: int) -> sqlite3.Row | None:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT parent_id
            FROM role_hierarchy
            WHERE role_id = ?
            """,
            (id,),
        ).fetchall()
    
    def get_child_roles(self, parent_id: int) -> sqlite3.Row | None:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT role_id
            FROM role_hierarchy
            WHERE parent_id = ?
            """, 
            (parent_id,)
        ).fetchall()
  
    def get_role_permissions(self, id: int) -> list[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT p.id, p.name, rp.value
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = ?
            """,
            (id,),
        ).fetchall()
    
    def list_roles(self) -> list[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(
            "SELECT id, name, description FROM roles ORDER BY id"
        ).fetchall()


    # permissions
    @with_txn
    def insert_permission(self, conn: sqlite3.Connection, *, name: str, description: str):
        conn.execute(
            """
            INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)
            """,
            (name, description)
        )

    @with_txn
    def update_permission(self, conn: sqlite3.Connection, *, id: int, name: str, description: str):
        conn.execute(
            """
            UPDATE permissions SET name = ?, description = ? 
            WHERE id = ?
            """,
            (name, description, id)
        )
        
    @with_txn
    def delete_permission(self, conn: sqlite3.Connection, *, permission_id: int):
        conn.execute("DELETE FROM permissions WHERE id = ?", (permission_id,))

    def get_permission_by_id(self, id: int) -> sqlite3.Row:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, name, description FROM permissions 
            WHERE id = ?
            """, 
            (id,)
        ).fetchone()
    
    def get_permission_by_name(self, name: str) -> sqlite3.Row:
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, name, description FROM permissions 
            WHERE name = ?
            """, 
            (name,)
        ).fetchone()
        
    def list_permissions(self):
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, name, description FROM permissions
            ORDER BY id
            """
        ).fetchall()


    @with_txn
    def insert_conversation(
        self, 
        conn: sqlite3.Connection,
        *, 
        conv_id: bytes, 
        user_id: bytes,
        title: str,
        metadata_json: str,
        ts: int):

        conn.execute(
            """
            INSERT INTO conversations
            (id, user_id, title, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conv_id, user_id, title, metadata_json, ts, ts),
        )

    def get_conversation(self, user_id: bytes,
                              limit: int, offset: int):

        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, title, metadata_json, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ).fetchall()
    
    @with_txn
    def update_conversation_title(self, conn: sqlite3.Connection, *, user_id: bytes, c_id: bytes, title: str):
        conn.execute(
            """
            UPDATE conversations SET title = ? WHERE id = ? AND user_id = ?
            """,
            (title, c_id, user_id)
        )
    
    @with_txn
    def update_conversation_updated_at(self, conn: sqlite3.Connection, *, c_id: bytes, ts:int):
        conn.execute(
            """
            UPDATE conversations SET updated_at = ? WHERE id = ?
            """, 
            (ts, c_id)
        )

    @with_txn
    def delete_conversation(self, conn:sqlite3.Connection, *, user_id: bytes, c_id: bytes):
        conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (c_id, user_id))

    @with_txn
    def insert_message(
        self, 
        conn: sqlite3.Connection,
        *, 
        msg_id: bytes,
        c_id: bytes,
        role: str,
        metadata: str,
        content: str,
        options: str,
        ts: int):

        conn.execute(
            """
            INSERT INTO messages
            (id, c_id, role, metadata, content, options, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, c_id, role, metadata, content, options, ts)
        )

    def get_messages(self, c_id: bytes, limit: int):
        conn = self._get_conn()
        return conn.execute(
            """
            SELECT id, role, metadata, content, options, created_at
            FROM messages
            WHERE c_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (c_id, limit),
        ).fetchall()
    
    @with_txn
    def delete_message(self, conn: sqlite3.Connection, *, c_id: bytes, msg_id: bytes):
        conn.execute("DELETE FROM messages WHERE id = ? AND c_id = ?", (msg_id, c_id))
