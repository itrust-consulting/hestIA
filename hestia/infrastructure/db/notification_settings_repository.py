from __future__ import annotations

import sqlite3
import threading
import time
from typing import Any, Dict, Optional

from hestia.infrastructure.db.user_repository import with_txn

# Kept in sync with NotificationService's hardcoded fallback -- this is the
# seed content for a genuinely fresh install; once the row exists an admin
# may have edited it, so initialize() never overwrites it again.
DEFAULT_WELCOME_TITLE = "Welcome to hestIA!"
DEFAULT_WELCOME_BODY = (
    "Here's a quick tour to get you started:\n\n"
    "- **Chat** — type your question in the message box at the bottom of the screen and press Enter.\n"
    "- **Ask My Docs (RAG)** — click **Ask My Docs** in the sidebar (or press `Ctrl+Shift+D`) to have "
    "the assistant answer using your organization's documents instead of general knowledge.\n"
    "- **Pick a corpus** — in the Ask My Docs panel, choose one from **Select a corpus…** and click "
    "**Select** to activate it.\n"
    "- **Join a tenant** — go to **Account → Tenants**, search for your team, and click "
    "**Request to Join** to get access to its knowledge bases.\n"
    "- **Need more help?** Visit the [Help Center](/help) for detailed guidance."
)


def _now_ms() -> int:
    return int(time.time() * 1000)


class NotificationSettingsRepository:
    """Admin-editable notification config -- currently just the welcome
    message sent to new users. A single row (id=1), seeded once on a
    genuinely fresh install, then DB is the source of truth. Mirrors
    AuthSettingsRepository's seed-once-then-DB-owns-it pattern."""

    def __init__(self, get_conn: callable, db_lock: threading.Lock):
        self._get_conn = get_conn
        self._db_lock = db_lock

    @with_txn
    def initialize(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notification_settings (
              id            INTEGER PRIMARY KEY CHECK (id = 1),
              welcome_title TEXT NOT NULL DEFAULT '',
              welcome_body  TEXT NOT NULL DEFAULT '',
              updated_at    INTEGER NOT NULL
            );
            """
        )

        has_row = conn.execute("SELECT 1 FROM notification_settings WHERE id = 1").fetchone()
        if has_row:
            return

        conn.execute(
            "INSERT INTO notification_settings (id, welcome_title, welcome_body, updated_at) VALUES (1, ?, ?, ?)",
            (DEFAULT_WELCOME_TITLE, DEFAULT_WELCOME_BODY, _now_ms()),
        )

    def get_settings(self) -> Optional[Dict[str, Any]]:
        r = self._get_conn().execute("SELECT * FROM notification_settings WHERE id = 1").fetchone()
        return dict(r) if r else None

    @with_txn
    def update_settings(self, conn: sqlite3.Connection, **fields: Any) -> None:
        """Partial update -- only columns present (and non-None) in `fields`
        are written. `fields` uses the same keys as the table's columns."""
        set_clauses = []
        values = []
        for key, value in fields.items():
            if value is None:
                continue
            set_clauses.append(f"{key} = ?")
            values.append(value)
        if not set_clauses:
            return
        set_clauses.append("updated_at = ?")
        values.append(_now_ms())
        conn.execute(f"UPDATE notification_settings SET {', '.join(set_clauses)} WHERE id = 1", values)
