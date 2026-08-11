from __future__ import annotations

import sqlite3
import threading

from hestia.infrastructure.db.user_repository import with_txn


class SyncManifestRepository:
    """Tracks per-document content hashes for upload sources (Sync Folder
    folders, and the plain 'Add Document' modal via a fixed 'manual' sync_id),
    scoped by (collection, sync_id). Stored independently of Qdrant because a
    document can legitimately produce zero chunks (and therefore zero Qdrant
    points) while still needing a durable per-document hash record.

    Also tracks, per (collection, content_hash), which single source_uri
    actually owns the real Qdrant content for that hash -- every other
    source_uri sharing that hash is a reference that piggybacks on the
    owner's content without having any Qdrant data of its own. This is what
    lets identical content uploaded through multiple sync sources (or the
    plain upload modal) get embedded/stored exactly once collection-wide."""

    def __init__(self, get_conn: callable, db_lock: threading.Lock):
        self._get_conn = get_conn
        self._db_lock = db_lock

    @with_txn
    def initialize(self, conn: sqlite3.Connection):
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_manifest (
              collection    TEXT NOT NULL,
              sync_id       TEXT NOT NULL,
              source_uri    TEXT NOT NULL,
              content_hash  TEXT NOT NULL,
              updated_at    INTEGER NOT NULL,
              PRIMARY KEY (collection, sync_id, source_uri)
            );

            CREATE TABLE IF NOT EXISTS content_owners (
              collection        TEXT NOT NULL,
              content_hash      TEXT NOT NULL,
              owner_source_uri  TEXT NOT NULL,
              PRIMARY KEY (collection, content_hash)
            );

            CREATE TABLE IF NOT EXISTS sync_runs (
              collection      TEXT NOT NULL,
              sync_id         TEXT NOT NULL,
              last_synced_at  INTEGER NOT NULL,
              PRIMARY KEY (collection, sync_id)
            );
            """
        )

    def get_manifest(self, collection: str, sync_id: str) -> dict[str, str]:
        rows = self._get_conn().execute(
            "SELECT source_uri, content_hash FROM sync_manifest WHERE collection=? AND sync_id=?",
            (collection, sync_id),
        ).fetchall()
        return {row["source_uri"]: row["content_hash"] for row in rows}

    @with_txn
    def upsert_entry(
        self,
        conn: sqlite3.Connection,
        collection: str,
        sync_id: str,
        source_uri: str,
        content_hash: str,
        updated_at: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO sync_manifest (collection, sync_id, source_uri, content_hash, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (collection, sync_id, source_uri)
            DO UPDATE SET content_hash = excluded.content_hash, updated_at = excluded.updated_at
            """,
            (collection, sync_id, source_uri, content_hash, updated_at),
        )

    @with_txn
    def delete_entry(self, conn: sqlite3.Connection, collection: str, source_uri: str) -> None:
        conn.execute(
            "DELETE FROM sync_manifest WHERE collection=? AND source_uri=?",
            (collection, source_uri),
        )

    def get_hash_for_source(self, collection: str, source_uri: str) -> str | None:
        row = self._get_conn().execute(
            "SELECT content_hash FROM sync_manifest WHERE collection=? AND source_uri=? "
            "ORDER BY updated_at DESC LIMIT 1",
            (collection, source_uri),
        ).fetchone()
        return row["content_hash"] if row else None

    def get_owner(self, collection: str, content_hash: str) -> str | None:
        row = self._get_conn().execute(
            "SELECT owner_source_uri FROM content_owners WHERE collection=? AND content_hash=?",
            (collection, content_hash),
        ).fetchone()
        return row["owner_source_uri"] if row else None

    @with_txn
    def claim_owner(self, conn: sqlite3.Connection, collection: str, content_hash: str, source_uri: str) -> str:
        """Atomically claim ownership of (collection, content_hash) for source_uri
        if unclaimed. Returns the actual owner after the attempt -- may be a
        different source_uri if this content was already owned (by this call
        or a concurrent one that won the race)."""
        conn.execute(
            "INSERT INTO content_owners (collection, content_hash, owner_source_uri) VALUES (?, ?, ?) "
            "ON CONFLICT (collection, content_hash) DO NOTHING",
            (collection, content_hash, source_uri),
        )
        row = conn.execute(
            "SELECT owner_source_uri FROM content_owners WHERE collection=? AND content_hash=?",
            (collection, content_hash),
        ).fetchone()
        return row["owner_source_uri"]

    def get_references(self, collection: str, content_hash: str) -> list[str]:
        """All source_uris (across every sync_id) currently tracking this
        content_hash, oldest first -- used to pick a deterministic handoff
        target when the current owner is deleted."""
        rows = self._get_conn().execute(
            "SELECT DISTINCT source_uri FROM sync_manifest WHERE collection=? AND content_hash=? "
            "ORDER BY updated_at ASC",
            (collection, content_hash),
        ).fetchall()
        return [row["source_uri"] for row in rows]

    @with_txn
    def reassign_owner(self, conn: sqlite3.Connection, collection: str, content_hash: str, new_owner: str) -> None:
        conn.execute(
            "UPDATE content_owners SET owner_source_uri=? WHERE collection=? AND content_hash=?",
            (new_owner, collection, content_hash),
        )

    @with_txn
    def remove_owner(self, conn: sqlite3.Connection, collection: str, content_hash: str) -> None:
        conn.execute(
            "DELETE FROM content_owners WHERE collection=? AND content_hash=?",
            (collection, content_hash),
        )

    def get_last_synced_at(self, collection: str, sync_id: str) -> int | None:
        row = self._get_conn().execute(
            "SELECT last_synced_at FROM sync_runs WHERE collection=? AND sync_id=?",
            (collection, sync_id),
        ).fetchone()
        return row["last_synced_at"] if row else None

    @with_txn
    def mark_synced(self, conn: sqlite3.Connection, collection: str, sync_id: str, when: int) -> None:
        conn.execute(
            """
            INSERT INTO sync_runs (collection, sync_id, last_synced_at)
            VALUES (?, ?, ?)
            ON CONFLICT (collection, sync_id)
            DO UPDATE SET last_synced_at = excluded.last_synced_at
            """,
            (collection, sync_id, when),
        )

    @with_txn
    def delete_collection(self, conn: sqlite3.Connection, collection: str) -> None:
        """Clear every row tracked for this collection across all three tables.
        Must be called whenever the underlying Qdrant collection is deleted --
        otherwise stale content_owners rows would silently cause a future
        collection recreated under the same name to skip real uploads as
        'already owned' duplicates, even though no such content exists in the
        (new, empty) Qdrant collection anymore."""
        conn.execute("DELETE FROM sync_manifest WHERE collection=?", (collection,))
        conn.execute("DELETE FROM content_owners WHERE collection=?", (collection,))
        conn.execute("DELETE FROM sync_runs WHERE collection=?", (collection,))
