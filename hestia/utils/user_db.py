import sqlite3
import threading

from hestia.settings import CDB_PATH

BUSY_TIMEOUT_MS = 5000

_local = threading.local()
_db_lock = threading.Lock()

def get_conn() -> sqlite3.Connection:
    """
    Create a thread-local connection in non-autocommit mode (isolation_level='DEFERRED').
    This lets us use BEGIN/COMMIT/ROLLBACK reliably.
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        # Use default isolation_level='DEFERRED' (the default if you don't pass None).
        conn = sqlite3.connect(CDB_PATH, check_same_thread=False)  # NOT autocommit
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

def with_txn(fn):
    def wrapper(self, *args, **kwargs):
        with _db_lock:
            conn = get_conn()
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

    @with_txn
    def initialize(self, conn: sqlite3.Connection):
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id                    BLOB(16) PRIMARY KEY,
              username              TEXT NOT NULL UNIQUE,
              password_hash         BLOB NOT NULL,
              salt                  BLOB NOT NULL,
              must_change_pw        INTEGER NOT NULL DEFAULT 1,
              created_at            INTEGER NOT NULL,
              updated_at            INTEGER NOT NULL
            );

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

            CREATE TABLE IF NOT EXISTS roles (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                description         TEXT
            );

            CREATE TABLE IF NOT EXISTS permissions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL UNIQUE,
                description         TEXT
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id             INTEGER NOT NULL,
                permission_id       INTEGER NOT NULL,
                value               TEXT,
                PRIMARY KEY         (role_id, permission_id),
                FOREIGN KEY         (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY         (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_roles (
                user_id             BLOB(16) NOT NULL,
                role_id             INTEGER NOT NULL,
                PRIMARY KEY         (user_id, role_id),
                FOREIGN KEY         (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY         (role_id) REFERENCES roles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS role_hierarchy (
                role_id   INTEGER NOT NULL,
                parent_id INTEGER NOT NULL,
                PRIMARY KEY(role_id, parent_id),
                FOREIGN KEY(role_id)   REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_id) REFERENCES roles(id) ON DELETE CASCADE
            );

            INSERT OR IGNORE INTO roles (name, description) VALUES
                ('admin', 'Full system access'),
                ('moderator', 'Access to content management features'),
                ('isms_member', 'Information Security Management System team member'),
                ('auditor', 'Internal and external ISMS auditor'),
                ('user', 'Access to general system features'),
                ('guest', 'Only chat access' );
            
            INSERT OR IGNORE INTO role_hierarchy (role_id, parent_id) VALUES
                ((SELECT id FROM roles WHERE name='user'),
                (SELECT id FROM roles WHERE name='guest')),

                ((SELECT id FROM roles WHERE name='auditor'),
                (SELECT id FROM roles WHERE name='user')),

                ((SELECT id FROM roles WHERE name='isms_member'),
                (SELECT id FROM roles WHERE name='user')),

                ((SELECT id FROM roles WHERE name='moderator'),
                (SELECT id FROM roles WHERE name='user')),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM roles WHERE name='moderator'));

            INSERT OR IGNORE INTO permissions (name, description) VALUES
                ('manage_users', 'Create, delete, and edit users'),
                ('assign_roles', 'Assign roles to users'),
                ('view_users', 'View list of users'),

                ('use_rag', 'Use retrieval-augmented generation'),
                ('max_classification', 'Maximum document classification level accessible'),
                ('allowed_collections', 'Collections that the user may access'),

                ('configure_llm', 'Configure LLM model and settings'),
                ('view_llm_status', 'View LLM system status'),

                ('manage_system', 'Change general system settings'),
                ('manage_database', 'Backup, vacuum, or alter the database'),
                ('view_system_status', 'View system health and metrics'),

                ('manage_documents', 'Upload or delete knowledge base documents'),
                ('manage_collections', 'Manage RAG collection settings'),
                ('reindex_corpus', 'Re-index or rebuild the document store');


            INSERT OR IGNORE INTO role_permissions (role_id, permission_id, value)
                VALUES
                ((SELECT id FROM roles WHERE name='guest'),
                (SELECT id FROM permissions WHERE name='view_llm_status'),
                'true');

            INSERT OR IGNORE INTO role_permissions (role_id, permission_id, value)
                VALUES
                ((SELECT id FROM roles WHERE name='user'),
                (SELECT id FROM permissions WHERE name='use_rag'),
                'true'),

                ((SELECT id FROM roles WHERE name='user'),
                (SELECT id FROM permissions WHERE name='max_classification'),
                '1'),

                ((SELECT id FROM roles WHERE name='user'),
                (SELECT id FROM permissions WHERE name='allowed_collections'),
                '["ITR ISMS"]');

            
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id, value)
                VALUES
                ((SELECT id FROM roles WHERE name='isms_member'),
                (SELECT id FROM permissions WHERE name='max_classification'),
                '4');

            INSERT OR IGNORE INTO role_permissions (role_id, permission_id, value)
                VALUES
                ((SELECT id FROM roles WHERE name='auditor'),
                (SELECT id FROM permissions WHERE name='max_classification'),
                '3');

            INSERT OR IGNORE INTO role_permissions (role_id, permission_id, value)
                VALUES
                ((SELECT id FROM roles WHERE name='moderator'),
                (SELECT id FROM permissions WHERE name='manage_documents'),
                'true'),

                ((SELECT id FROM roles WHERE name='moderator'),
                (SELECT id FROM permissions WHERE name='manage_collections'),
                'true'),

                ((SELECT id FROM roles WHERE name='moderator'),
                (SELECT id FROM permissions WHERE name='reindex_corpus'),
                'true');

            INSERT OR IGNORE INTO role_permissions (role_id, permission_id, value)
                VALUES
                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='manage_users'),
                'true'),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='assign_roles'),
                'true'),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='view_users'),
                'true'),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='assign_roles'),
                'true'),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='configure_llm'),
                'true'),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='manage_system'),
                'true'),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='manage_database'),
                'true'),

                ((SELECT id FROM roles WHERE name='admin'),
                (SELECT id FROM permissions WHERE name='view_system_status'),
                'true');

            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(c_id, created_at, id);
            CREATE INDEX IF NOT EXISTS idx_users_roles ON user_roles(user_id);
            CREATE INDEX IF NOT EXISTS idx_role_permissions ON role_permissions(role_id);
            """
        )

    @with_txn
    def insert_user(self, conn: sqlite3.Connection,
                    user_id: bytes,
                    username: str,
                    password_hash: bytes,
                    salt: bytes,
                    created_ts: int):

        conn.execute(
            """
            INSERT INTO users (id, username, password_hash, salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, password_hash, salt, created_ts, created_ts),
        )

    def get_user_by_id(self, user_id: bytes) -> sqlite3.Row:
        conn = get_conn()
        return conn.execute(
            """
            SELECT id, username, password_hash, salt, must_change_pw, created_at, updated_at 
            FROM users WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    def get_user_by_username(self, username: str) -> sqlite3.Row:
        conn = get_conn()
        return conn.execute(
            """
            SELECT id, username, password_hash, salt, must_change_pw, created_at, updated_at 
            FROM users WHERE username = ?
            """,
            (username,),
        ).fetchone()

    def list_users(self):
        conn = get_conn()
        return conn.execute(
                """
                SELECT 
                    u.id,
                    u.username,
                    u.created_at,
                    u.updated_at,
                    GROUP_CONCAT(r.name, ',') AS roles
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN roles r ON ur.role_id = r.id
                GROUP BY u.id, u.username, u.created_at, u.updated_at
                ORDER BY u.username ASC
                """
                ).fetchall()

    @with_txn
    def delete_user(self, conn: sqlite3.Connection, user_id: bytes):
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    @with_txn
    def clear_must_change_pw(self, conn:sqlite3.Connection, user_id: bytes, updated_ts: int):
        conn.execute(
            "UPDATE users SET must_change_pw = 0, updated_at = ? WHERE id = ?",
            (updated_ts, user_id)
        )

    @with_txn
    def update_password(self, conn: sqlite3.Connection,
                        user_id: bytes,
                        new_hash: bytes,
                        new_salt: bytes,
                        updated_ts: int):

        conn.execute(
            """
            UPDATE users SET password_hash = ?, salt = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_hash, new_salt, updated_ts, user_id),
        )


    def list_roles(self):
        conn = get_conn()
        return conn.execute(
            "SELECT id, name, description FROM roles ORDER BY id"
        ).fetchall()

    def get_parent_roles(self, role_id: int):
        conn = get_conn()
        return conn.execute(
            """
            SELECT parent_id
            FROM role_hierarchy
            WHERE role_id = ?
            """,
            (role_id,),
        ).fetchall()
        
    def get_role_permissions(self, role_id: int):
        conn = get_conn()
        return conn.execute(
            """
            SELECT p.name, rp.value
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = ?
            """,
            (role_id,),
        ).fetchall()
    
    @with_txn
    def set_role_permission(
        conn: sqlite3.Connection,
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
        
    def get_user_roles(self, user_id: bytes):
        conn = get_conn()
        return conn.execute(
            """
            SELECT roles.id, roles.name, roles.description FROM roles
            JOIN user_roles ON roles.id = user_roles.role_id
            WHERE user_roles.user_id = ?
            """,
            (user_id,)
        ).fetchall()
    
    @with_txn
    def add_role_to_user(self, conn: sqlite3.Connection, user_id: bytes, role_id: int):
        conn.execute(
            """
            INSERT OR IGNORE INTO user_roles (user_id, role_id)
            Values (?, ?)
            """,
            (user_id, role_id)
        )

    @with_txn
    def remove_role_from_user(self, conn: sqlite3.Connection, user_id: bytes, role_id: int):
        conn.execute(
            "DELETE FROM user_roles WHERE user_id = ? AND role_id = ?",
            (user_id, role_id)
        )


    @with_txn
    def insert_conversation(self, conn: sqlite3.Connection,
                            conv_id: bytes, user_id: bytes,
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

        conn = get_conn()
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
    def update_conversation_title(self, conn: sqlite3.Connection, user_id: bytes, c_id: bytes, title: str):
        conn.execute(
            """
            UPDATE conversations SET title = ? WHERE id = ? AND user_id = ?
            """,
            (title, c_id, user_id)
        )
    
    @with_txn
    def update_conversation_updated_at(self, conn: sqlite3.Connection, c_id: bytes, ts:int):
        conn.execute(
            """
            UPDATE conversations SET updated_at = ? WHERE id = ?
            """, 
            (ts, c_id)
        )

    @with_txn
    def delete_conversation(self, conn:sqlite3.Connection, user_id: bytes, c_id: bytes):
        conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (c_id, user_id))

    @with_txn
    def insert_message(self, conn: sqlite3.Connection,
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
        conn = get_conn()
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
    def delete_message(self, conn: sqlite3.Connection, c_id: bytes, msg_id: bytes):
        conn.execute("DELETE FROM messages WHERE id = ? AND c_id = ?", (msg_id, c_id))
