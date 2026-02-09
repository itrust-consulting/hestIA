import time
import uuid
import sqlite3
import threading
import secrets
import hashlib
import datetime as dt
from typing import List, Tuple, Optional, Dict, Any


import hestia.settings as settings
# =========================
# Configuration
# =========================
DB_PATH = settings.CDB_PATH

PBKDF2_ITERATIONS = 210_000  # OWASP-recommended range; reasonable default
SALT_BYTES = 16  # 128-bit salt
BUSY_TIMEOUT_MS = 5000


MAX_HISTORY_PAIRS = 10       # Limit messages loaded into UI


# =========================
# Database setup & helpers
# =========================

_local = threading.local()
_db_lock = threading.Lock()

_conn: Optional[sqlite3.Connection] = None


def new_uuid() -> uuid.UUID:
    return uuid.uuid4().bytes 

def uuid_to_str(u: uuid.UUID) -> str:
    return str(uuid.UUID(bytes=u))

def uuid_from_str(s: str) -> uuid.UUID:
    return uuid.UUID(s).bytes



def _now_epoch() -> int:
    return int(time.time())

def get_conn() -> sqlite3.Connection:
    """
    Create a thread-local connection in non-autocommit mode (isolation_level='DEFERRED').
    This lets us use BEGIN/COMMIT/ROLLBACK reliably.
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        # Use default isolation_level='DEFERRED' (the default if you don't pass None).
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)  # NOT autocommit
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

def with_txn(fn, *args, **kwargs):
    """
    Run `fn(conn, *args, **kwargs)` inside a short transaction.
    - Serialize writes with a global lock (_db_lock).
    - Uses BEGIN/COMMIT/ROLLBACK (no SAVEPOINTs) for simplicity.
    - Assumes you do NOT call with_txn() inside with_txn() (avoid nested transactions).
    """
    with _db_lock:
        conn = get_conn()
        try:
            conn.execute("BEGIN;")       # DEFERRED; upgrade to write lock on first write
            result = fn(conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

def init_db():
    def _create(conn: sqlite3.Connection):
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id            BLOB(16) PRIMARY KEY,
              username      TEXT NOT NULL UNIQUE,
              password_hash BLOB NOT NULL,
              salt          BLOB NOT NULL,
              created_at    INTEGER NOT NULL,
              updated_at    INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
              id            BLOB(16) PRIMARY KEY,
              user_id       BLOB(16) NOT NULL,
              title         TEXT,
              metadata_json TEXT,
              created_at    INTEGER NOT NULL,
              updated_at    INTEGER NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
              id              BLOB(16) PRIMARY KEY,
              c_id            BLOB(16) NOT NULL,
              role            TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
              metadata        TEXT,
              content         TEXT NOT NULL,
              options         TEXT,
              created_at      INTEGER NOT NULL,
              FOREIGN KEY (c_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(c_id, created_at, id);
            """
        )
    with_txn(_create)

def _make_salt(n: int = SALT_BYTES) -> bytes:
    return secrets.token_bytes(n)

def _hash_password(password: str, salt: bytes) -> bytes:
    # PBKDF2-SHA256; stdlib-only; adjust iterations via env if needed
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32)

def _timing_safe_eq(a: bytes, b: bytes) -> bool:
    return secrets.compare_digest(a, b)



def register_user(username: str, password: str) -> None:
    
    """
    Create a user. Returns user_id.
    Raises ValueError if invalid input or username already exists.
    """
    username = (username or "").strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    user_id = new_uuid()
    salt = _make_salt()
    pwd_hash = _hash_password(password, salt)
    ts = _now_epoch()

    def _insert(conn: sqlite3.Connection):
        try:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, salt, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, pwd_hash, salt, ts, ts),
            )
            return user_id
        except sqlite3.IntegrityError as e:
            # Likely UNIQUE(username)
            raise ValueError("Username already exists.") from e

    return with_txn(_insert)


def authenticate(username: str, password: str) -> Tuple[bool, str, Optional[uuid.UUID]]:
    """
    Verify credentials. Returns user_id if valid, else None.
    """
    NACK = 0
    ACK = 1
    NACK_MSG = "Invalid username or password."
    ACK_MSG = "Login successful."

    username = (username or "").strip()
    if not username or not password:
        return NACK, NACK_MSG, None

    conn = get_conn()
    row = conn.execute(
        "SELECT id, password_hash, salt FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if not row:
        return NACK, NACK_MSG, None

    candidate = _hash_password(password, row["salt"])
    if _timing_safe_eq(candidate, row["password_hash"]):
        return ACK, ACK_MSG, row["id"]
    return NACK, NACK_MSG, None


def change_password(user_id: uuid.UUID, curr_pw: str, new_pw: str) -> bool:
    """
    Change password for an authenticated user.
    Returns True on success, False if current_password is wrong.

    Security:
    - Verifies current password first (timing-safe)
    - Uses a fresh random salt
    - PBKDF2 iterations from config
    """
    if not new_pw or len(new_pw) < 6:
        raise ValueError("New password must be at least 6 characters.")

    # Step 1: fetch current hash & salt
    conn = get_conn()
    row = conn.execute(
        "SELECT password_hash, salt FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        # user_id not found (shouldn't happen for logged-in users)
        return False

    # Step 2: verify current password
    candidate = _hash_password(curr_pw, row["salt"])
    if not _timing_safe_eq(candidate, row["password_hash"]):
        return False

    # Step 3: create new hash with fresh salt, update atomically
    new_salt = _make_salt()
    new_hash = _hash_password(new_pw, new_salt)
    ts = _now_epoch()

    def _upd(conn: sqlite3.Connection):
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?",
            (new_hash, new_salt, ts, user_id),
        )
        return True

    return with_txn(_upd)


def delete_account(user_id: uuid.UUID | str) -> None:
    """Delete a user and cascade-delete their conversations/messages."""
    if isinstance(user_id, str):
        user_id = uuid_from_str(user_id)
    def _del(conn: sqlite3.Connection):
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    with_txn(_del)


def create_conversation(user_id: uuid.UUID, title: Optional[str] = None, metadata_json: Optional[str] = None) -> uuid.UUID:
    ts = _now_epoch()
    id = new_uuid()
    def _ins(conn: sqlite3.Connection):
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, metadata_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (id, user_id, title, metadata_json, ts, ts),
        )
        return id

    return with_txn(_ins)

def delete_conversation(c_id: uuid.UUID):
    pass

def list_conversations(user_id: uuid.UUID, limit: int = 30, offset: int = 0):
    def _ret(conn: sqlite3.Connection):
        cur = conn.execute(
            "SELECT id, title, metadata_json "
            "FROM conversations WHERE user_id = ? "
            "ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset)
        ).fetchall()
        return [dict(r) for r in reversed(cur)]

    return with_txn(_ret) 

def _verify_user_affiliation(user_id, c_id) -> bool:
    def _ver(conn: sqlite3.Connection):
        cur = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (c_id, user_id)
        ).fetchone()
        return cur
    return with_txn(_ver)

def append_message(user_id: uuid.UUID, c_id: uuid.UUID, role: str, metadata: str, content: str, options: str) -> uuid.UUID:
    if not _verify_user_affiliation(user_id, c_id):
        return []
    
    ts = _now_epoch()
    id = new_uuid()

    def _ins(conn:sqlite3.Connection):
        conn.execute(
            "INSERT INTO messages (id, c_id, role, metadata, content, options, created_at) \
                VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id, c_id, role, json.dumps(metadata), json.dumps(content), json.dumps(options), ts)
        )
        return id
    
    return with_txn(_ins)


def load_messages(user_id: uuid.UUID, c_id: uuid.UUID, num_m: int = 30) -> Optional[Dict[str, Any]]:
    if not _verify_user_affiliation(user_id, c_id):
        return []
    
    def _ret(conn: sqlite3.Connection):
        rows = conn.execute( 
            "SELECT role, metadata, content, options "
            "FROM messages WHERE c_id = ?"
            "ORDER BY id DESC LIMIT ?",
            (c_id, num_m),
        ).fetchall()

        messages = []
        for row in rows:
            role = row["role"]
            metadata = json.loads(row["metadata"])
            content = json.loads(row["content"])
            options = json.loads(row["options"])
            
            messages.append({
                "role": role,
                "metadata": metadata,
                "content": [content],
                "options": options
            })
            
        return [r for r in reversed(messages)]
    
    return with_txn(_ret)

import json
if __name__=="__main__":
    init_db()
    user = "hfries"
    new_pw = "ITRUSThfries"
    try:
        reg_succ=register_user(username=user, password=new_pw)
        print(reg_succ)
    except ValueError as e:
        print(e)

    _, _, id = authenticate(username=user, password=new_pw)
    vid = uuid_to_str(id)
    create_conversation(id, "SOME UNIQUE TITLE")
    create_conversation(id, "ANOTHER UNIQUE TITLE")
    cids = list_conversations(id)

    messages = [{'role': 'user', 'metadata': None, 'content': [{'text': 'hello again', 'type': 'text'}], 'options': None}, 
                {'role': 'assistant', 'metadata': None, 'content': [{'text': 'Hello! 😊 How’s it going? What can I help you with today?', 'type': 'text'}], 'options': None}, 
                {'role': 'user', 'metadata': None, 'content': [{'text': 'What do you know about gradio? Keep your answer in 2-3 sentences', 'type': 'text'}], 'options': None}, 
                {'role': 'assistant', 'metadata': None, 'content': [{'text': '**Gradio** is an open-source Python library for quickly building and sharing interactive machine learning demos, web apps, and data visualization tools—with minimal code. It simplifies UI creation by providing pre-built components (like sliders, text boxes, and image uploaders) that work seamlessly with models (e.g., Hugging Face, TensorFlow, or PyTorch). Popular for deploying models as shareable web interfaces (e.g., via Gradio’s public hosting or self-hosted solutions).', 'type': 'text'}], 'options': None}]
    
    for m in messages:
        role = m["role"]
        metadata = m["metadata"]
        content = m["content"][0]
        options = m["options"]
        u_id = id
        c_id = cids[1]["id"]

        append_message(u_id, c_id, role, metadata, content, options)
    
    messages = []
    for cid in cids:
        messages.append(load_messages(id, c_id))
    print(messages)
    close()

