from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from hestia.config.settings import Settings
from hestia.infrastructure.db.user_repository import with_txn

PURPOSES = ("generation", "embedding", "reranking", "vector_db")
PURPOSE_LABELS = {
    "generation": "Generation",
    "embedding": "Embedding",
    "reranking": "Reranking",
    "vector_db": "Vector Database",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _row_to_dict(r: sqlite3.Row, *, include_api_key: bool) -> Dict[str, Any]:
    d = {
        "id": r["id"],
        "purpose": r["purpose"],
        "label": PURPOSE_LABELS[r["purpose"]],
        "backend_type": r["backend_type"],
        "base_url": r["base_url"],
        "model": r["model"],
        "params": json.loads(r["params"] or "{}"),
        "is_active": bool(r["is_active"]),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }
    if include_api_key:
        d["api_key"] = r["api_key"]
    else:
        d["has_api_key"] = r["api_key"] is not None
    return d


class LLMSettingsRepository:
    """A connection backs one purpose (generation/embedding/reranking/
    vector_db), but a purpose may have several connections -- at most one of
    them `is_active` at a time (enforced by a partial UNIQUE index), which is
    the one container.py wires up as that purpose's live service. Seeded
    once, on a genuinely fresh install (empty table), from env-var Settings
    so existing deployments keep working unchanged until an admin edits them
    through the UI. Every connection is deletable -- seeding never re-runs
    once any connection exists, so a deleted purpose/connection stays
    deleted across restarts instead of reappearing."""

    def __init__(self, get_conn: callable, db_lock: threading.Lock):
        self._get_conn = get_conn
        self._db_lock = db_lock

    @with_txn
    def initialize(self, conn: sqlite3.Connection, settings: Settings) -> None:
        self._migrate_legacy_schema(conn)
        self._migrate_add_vector_db_purpose(conn)
        self._migrate_add_multi_backend_support(conn)

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS llm_connections (
              id           INTEGER PRIMARY KEY AUTOINCREMENT,
              purpose      TEXT NOT NULL CHECK (purpose IN ('generation','embedding','reranking','vector_db')),
              backend_type TEXT NOT NULL CHECK (backend_type IN ('ollama','openai','qdrant')),
              base_url     TEXT NOT NULL,
              api_key      TEXT,
              model        TEXT NOT NULL DEFAULT '',
              params       TEXT NOT NULL DEFAULT '{}',
              is_active    INTEGER NOT NULL DEFAULT 0,
              created_at   INTEGER NOT NULL,
              updated_at   INTEGER NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_connections_active_purpose
              ON llm_connections(purpose) WHERE is_active = 1;
            """
        )

        # Only seed on a genuinely fresh install -- once any row exists, an
        # admin may have intentionally deleted one of the others, and
        # re-checking per-purpose on every startup would silently resurrect
        # a deleted connection on the next restart.
        has_any = conn.execute("SELECT 1 FROM llm_connections LIMIT 1").fetchone()
        if has_any:
            return

        llm_backend_type = "ollama" if settings.llm_backend == "ollama" else "openai"
        seed = {
            "generation": (llm_backend_type, settings.llm_url, settings.llm_api_key, settings.default_gen_model),
            "embedding": (llm_backend_type, settings.emb_url, settings.llm_api_key, settings.default_emb_model),
            "reranking": (llm_backend_type, settings.rrk_url, settings.llm_api_key, settings.default_rkk_model),
            "vector_db": (settings.db_backend, settings.db_url, settings.db_api_key, ""),
        }
        now = _now_ms()
        for purpose, (backend_type, base_url, api_key, model) in seed.items():
            conn.execute(
                "INSERT INTO llm_connections (purpose, backend_type, base_url, api_key, model, params, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, '{}', 1, ?, ?)",
                (purpose, backend_type, base_url, api_key, model or "", now, now),
            )

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        """One-time migration from an earlier iteration of this feature's
        schema (a shared llm_connections pool + a separate
        llm_purpose_configs assignment table) to the current one-row-per-
        purpose design. No-op if llm_connections doesn't exist yet, or
        already has the current `purpose` column."""
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(llm_connections)")}
        if not cols or "purpose" in cols:
            return

        conn.execute("ALTER TABLE llm_connections RENAME TO llm_connections_legacy")
        conn.execute("ALTER TABLE llm_purpose_configs RENAME TO llm_purpose_configs_legacy")
        conn.execute(
            """
            CREATE TABLE llm_connections (
              id           INTEGER PRIMARY KEY AUTOINCREMENT,
              purpose      TEXT NOT NULL UNIQUE CHECK (purpose IN ('generation','embedding','reranking')),
              backend_type TEXT NOT NULL CHECK (backend_type IN ('ollama','openai')),
              base_url     TEXT NOT NULL,
              api_key      TEXT,
              model        TEXT NOT NULL DEFAULT '',
              params       TEXT NOT NULL DEFAULT '{}',
              created_at   INTEGER NOT NULL,
              updated_at   INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO llm_connections (purpose, backend_type, base_url, api_key, model, params, created_at, updated_at)
            SELECT pc.purpose, c.backend_type, c.base_url, c.api_key, pc.model, pc.params, c.created_at, pc.updated_at
            FROM llm_purpose_configs_legacy pc
            JOIN llm_connections_legacy c ON c.id = pc.connection_id
            """
        )
        conn.execute("DROP TABLE llm_purpose_configs_legacy")
        conn.execute("DROP TABLE llm_connections_legacy")

    def _migrate_add_vector_db_purpose(self, conn: sqlite3.Connection) -> None:
        """One-time migration widening the `purpose`/`backend_type` CHECK
        constraints to allow 'vector_db'/'qdrant'. SQLite bakes CHECK
        constraints into the table at creation time, so a plain `CREATE
        TABLE IF NOT EXISTS` with the new constraint wouldn't touch an
        already-existing table. No-op if llm_connections doesn't exist yet,
        or its stored schema already mentions 'vector_db'."""
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'llm_connections'"
        ).fetchone()
        if row is None or "vector_db" in row["sql"]:
            return

        conn.execute("ALTER TABLE llm_connections RENAME TO llm_connections_pre_vector_db")
        conn.execute(
            """
            CREATE TABLE llm_connections (
              id           INTEGER PRIMARY KEY AUTOINCREMENT,
              purpose      TEXT NOT NULL UNIQUE CHECK (purpose IN ('generation','embedding','reranking','vector_db')),
              backend_type TEXT NOT NULL CHECK (backend_type IN ('ollama','openai','qdrant')),
              base_url     TEXT NOT NULL,
              api_key      TEXT,
              model        TEXT NOT NULL DEFAULT '',
              params       TEXT NOT NULL DEFAULT '{}',
              created_at   INTEGER NOT NULL,
              updated_at   INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO llm_connections (id, purpose, backend_type, base_url, api_key, model, params, created_at, updated_at) "
            "SELECT id, purpose, backend_type, base_url, api_key, model, params, created_at, updated_at "
            "FROM llm_connections_pre_vector_db"
        )
        conn.execute("DROP TABLE llm_connections_pre_vector_db")

    def _migrate_add_multi_backend_support(self, conn: sqlite3.Connection) -> None:
        """One-time migration dropping the UNIQUE(purpose) constraint (a
        purpose may now have several connections) and adding `is_active` so
        exactly one of them can be marked live per purpose (enforced by a
        partial unique index created alongside the main CREATE TABLE, right
        after this runs). No-op if llm_connections doesn't exist yet, or
        already has `is_active`. Every pre-existing row was, under the old
        constraint, its purpose's only connection -- so all of them become
        `is_active = 1`, preserving current behavior exactly."""
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(llm_connections)")}
        if not cols or "is_active" in cols:
            return

        conn.execute("ALTER TABLE llm_connections RENAME TO llm_connections_pre_multi_backend")
        conn.execute(
            """
            CREATE TABLE llm_connections (
              id           INTEGER PRIMARY KEY AUTOINCREMENT,
              purpose      TEXT NOT NULL CHECK (purpose IN ('generation','embedding','reranking','vector_db')),
              backend_type TEXT NOT NULL CHECK (backend_type IN ('ollama','openai','qdrant')),
              base_url     TEXT NOT NULL,
              api_key      TEXT,
              model        TEXT NOT NULL DEFAULT '',
              params       TEXT NOT NULL DEFAULT '{}',
              is_active    INTEGER NOT NULL DEFAULT 0,
              created_at   INTEGER NOT NULL,
              updated_at   INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO llm_connections (id, purpose, backend_type, base_url, api_key, model, params, is_active, created_at, updated_at) "
            "SELECT id, purpose, backend_type, base_url, api_key, model, params, 1, created_at, updated_at "
            "FROM llm_connections_pre_multi_backend"
        )
        conn.execute("DROP TABLE llm_connections_pre_multi_backend")

    def list_connections(self) -> List[Dict[str, Any]]:
        rows = self._get_conn().execute(
            "SELECT id, purpose, backend_type, base_url, api_key, model, params, is_active, created_at, updated_at "
            "FROM llm_connections ORDER BY purpose"
        ).fetchall()
        return [_row_to_dict(r, include_api_key=False) for r in rows]

    def get_connection(self, connection_id: int) -> Optional[Dict[str, Any]]:
        """Includes the raw api_key -- for internal provider construction only."""
        r = self._get_conn().execute(
            "SELECT id, purpose, backend_type, base_url, api_key, model, params, is_active, created_at, updated_at "
            "FROM llm_connections WHERE id = ?",
            (connection_id,),
        ).fetchone()
        return _row_to_dict(r, include_api_key=True) if r else None

    def get_connection_by_purpose(self, purpose: str) -> Optional[Dict[str, Any]]:
        """Returns the *active* connection for this purpose, if any -- a
        purpose can have zero, one, or several connections, but at most one
        active. container.py treats "no active connection" (whether from
        zero connections or none of several marked active) identically."""
        r = self._get_conn().execute(
            "SELECT id, purpose, backend_type, base_url, api_key, model, params, is_active, created_at, updated_at "
            "FROM llm_connections WHERE purpose = ? AND is_active = 1",
            (purpose,),
        ).fetchone()
        return _row_to_dict(r, include_api_key=True) if r else None

    @with_txn
    def create_connection(
        self, conn: sqlite3.Connection, *, purpose: str, backend_type: str, base_url: str, api_key: Optional[str],
    ) -> int:
        # The first connection ever configured for a purpose activates
        # itself automatically (so a previously-unconfigured purpose "just
        # works" in one step, same as before multi-backend support);
        # additional connections for an already-configured purpose land
        # inactive until explicitly activated.
        has_any_for_purpose = conn.execute(
            "SELECT 1 FROM llm_connections WHERE purpose = ?", (purpose,)
        ).fetchone()
        is_active = 0 if has_any_for_purpose else 1
        now = _now_ms()
        cur = conn.execute(
            "INSERT INTO llm_connections (purpose, backend_type, base_url, api_key, model, params, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, '', '{}', ?, ?, ?)",
            (purpose, backend_type, base_url, api_key or None, is_active, now, now),
        )
        return cur.lastrowid

    @with_txn
    def activate_connection(self, conn: sqlite3.Connection, *, connection_id: int) -> None:
        """Marks this connection active and every other connection sharing
        its purpose inactive -- in that order, so the partial unique index
        on (purpose) WHERE is_active never briefly sees two active rows for
        the same purpose."""
        row = conn.execute("SELECT purpose FROM llm_connections WHERE id = ?", (connection_id,)).fetchone()
        if row is None:
            raise ValueError("Connection not found.")
        conn.execute(
            "UPDATE llm_connections SET is_active = 0 WHERE purpose = ? AND id != ?",
            (row["purpose"], connection_id),
        )
        conn.execute(
            "UPDATE llm_connections SET is_active = 1, updated_at = ? WHERE id = ?",
            (_now_ms(), connection_id),
        )

    @with_txn
    def update_connection(
        self, conn: sqlite3.Connection, *, connection_id: int, base_url: str, api_key: Optional[str],
        model: str, params: Dict[str, Any],
    ) -> None:
        # A blank/omitted api_key means "keep the existing one" -- there's no
        # separate "clear the key" affordance in this iteration.
        if api_key:
            conn.execute(
                "UPDATE llm_connections SET base_url=?, api_key=?, model=?, params=?, updated_at=? WHERE id=?",
                (base_url, api_key, model, json.dumps(params or {}), _now_ms(), connection_id),
            )
        else:
            conn.execute(
                "UPDATE llm_connections SET base_url=?, model=?, params=?, updated_at=? WHERE id=?",
                (base_url, model, json.dumps(params or {}), _now_ms(), connection_id),
            )

    @with_txn
    def delete_connection(self, conn: sqlite3.Connection, *, connection_id: int) -> None:
        conn.execute("DELETE FROM llm_connections WHERE id = ?", (connection_id,))
