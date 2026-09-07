from __future__ import annotations

import pytest

from hestia.infrastructure.db.notification_settings_repository import (
    DEFAULT_WELCOME_BODY, DEFAULT_WELCOME_TITLE, NotificationSettingsRepository,
)
from hestia.infrastructure.db.user_repository import create_sqlite_connection


# ---------------------------------------------------------------------------
# Fixtures — real in-memory SQLite, no mocking the DB layer.
# ---------------------------------------------------------------------------

@pytest.fixture
def repo():
    get_conn, close, lock = create_sqlite_connection(":memory:")
    r = NotificationSettingsRepository(get_conn=get_conn, db_lock=lock)
    r.initialize()
    return r


# ---------------------------------------------------------------------------
# initialize — schema creation + seed-once semantics
# ---------------------------------------------------------------------------

class TestInitialize:

    def test_creates_table_and_seeds_default_row(self, repo):
        settings = repo.get_settings()
        assert settings is not None
        assert settings["id"] == 1
        assert settings["welcome_title"] == DEFAULT_WELCOME_TITLE
        assert settings["welcome_body"] == DEFAULT_WELCOME_BODY
        assert settings["updated_at"] > 0

    def test_is_idempotent_and_does_not_overwrite_a_seeded_row(self, repo):
        # initialize() runs on every app startup -- once an admin has edited
        # the row, a re-run must never stomp their changes back to defaults.
        repo.update_settings(welcome_title="Custom Title", welcome_body="Custom Body")

        repo.initialize()

        settings = repo.get_settings()
        assert settings["welcome_title"] == "Custom Title"
        assert settings["welcome_body"] == "Custom Body"

    def test_only_one_row_ever_exists(self, repo):
        repo.initialize()
        repo.initialize()
        conn = repo._get_conn()
        count = conn.execute("SELECT COUNT(*) AS c FROM notification_settings").fetchone()["c"]
        assert count == 1


# ---------------------------------------------------------------------------
# get_settings
# ---------------------------------------------------------------------------

class TestGetSettings:

    def test_returns_dict_with_all_columns(self, repo):
        settings = repo.get_settings()
        assert set(settings.keys()) == {"id", "welcome_title", "welcome_body", "updated_at"}

    def test_returns_none_when_row_absent(self, repo):
        conn = repo._get_conn()
        conn.execute("DELETE FROM notification_settings WHERE id = 1")
        conn.commit()

        assert repo.get_settings() is None


# ---------------------------------------------------------------------------
# update_settings — partial update semantics
# ---------------------------------------------------------------------------

class TestUpdateSettings:

    def test_updates_only_the_provided_field(self, repo):
        before = repo.get_settings()

        repo.update_settings(welcome_title="New Title", welcome_body=None)

        after = repo.get_settings()
        assert after["welcome_title"] == "New Title"
        assert after["welcome_body"] == before["welcome_body"]

    def test_updates_both_fields(self, repo):
        repo.update_settings(welcome_title="T", welcome_body="B")

        settings = repo.get_settings()
        assert settings["welcome_title"] == "T"
        assert settings["welcome_body"] == "B"

    def test_bumps_updated_at(self, repo):
        before = repo.get_settings()

        repo.update_settings(welcome_title="Bump")

        after = repo.get_settings()
        assert after["updated_at"] >= before["updated_at"]

    def test_no_fields_provided_is_a_noop(self, repo):
        before = repo.get_settings()

        repo.update_settings()

        assert repo.get_settings() == before

    def test_all_none_fields_is_a_noop(self, repo):
        before = repo.get_settings()

        repo.update_settings(welcome_title=None, welcome_body=None)

        assert repo.get_settings() == before
