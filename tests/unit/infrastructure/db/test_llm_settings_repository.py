from __future__ import annotations

import threading

import pytest

from hestia.config.settings import Settings
from hestia.infrastructure.db.llm_settings_repository import LLMSettingsRepository
from hestia.infrastructure.db.user_repository import create_sqlite_connection


@pytest.fixture
def repo():
    get_conn, close, lock = create_sqlite_connection(":memory:")
    r = LLMSettingsRepository(get_conn, lock)
    r.initialize(Settings())
    return r


def _conn(repo):
    return repo._get_conn()


# ---------------------------------------------------------------------------
# Migrations — each test seeds the exact pre-migration-N schema (the "old"
# CREATE TABLE literally embedded in migration N+1's own rename-away step)
# against a fresh :memory: DB, then runs the real initialize() and asserts
# the data survives into the fully-migrated schema. This is the same
# regression-test shape used for the ordering bug found in
# user_repository.py's tenant_collections migration.
# ---------------------------------------------------------------------------

class TestMigrateLegacySchema:

    def test_migrates_purpose_configs_data_into_new_one_row_per_purpose_schema(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        conn = get_conn()
        conn.executescript(
            """
            CREATE TABLE llm_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backend_type TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key TEXT,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE llm_purpose_configs (
                connection_id INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                params TEXT NOT NULL DEFAULT '{}',
                updated_at INTEGER NOT NULL
            );
            INSERT INTO llm_connections (id, backend_type, base_url, api_key, created_at)
                VALUES (1, 'openai', 'http://old-llm', 'oldkey', 100);
            INSERT INTO llm_purpose_configs (connection_id, purpose, model, params, updated_at)
                VALUES (1, 'generation', 'old-model', '{}', 200);
            """
        )
        conn.commit()

        repo = LLMSettingsRepository(get_conn, lock)
        repo.initialize(Settings())

        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "llm_purpose_configs" not in tables
        assert "llm_connections_legacy" not in tables
        assert "llm_purpose_configs_legacy" not in tables

        row = conn.execute("SELECT * FROM llm_connections WHERE purpose = 'generation'").fetchone()
        assert row is not None
        assert row["base_url"] == "http://old-llm"
        assert row["api_key"] == "oldkey"
        assert row["model"] == "old-model"
        assert row["is_active"] == 1  # preserved by the later multi-backend migration in the same initialize() call


class TestMigrateAddVectorDbPurpose:

    def test_widens_check_constraints_and_preserves_existing_rows(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        conn = get_conn()
        conn.executescript(
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
            );
            INSERT INTO llm_connections (purpose, backend_type, base_url, api_key, model, params, created_at, updated_at)
                VALUES ('embedding', 'ollama', 'http://old-emb', NULL, 'emb-model', '{}', 100, 100);
            """
        )
        conn.commit()

        repo = LLMSettingsRepository(get_conn, lock)
        repo.initialize(Settings())

        # A vector_db/qdrant row must now be insertable (CHECK constraint widened)
        conn.execute(
            "INSERT INTO llm_connections (purpose, backend_type, base_url, model, params, is_active, "
            "compaction_enabled, created_at, updated_at) VALUES ('vector_db', 'qdrant', 'http://q', '', '{}', 1, 0, 1, 1)"
        )
        conn.commit()

        row = conn.execute("SELECT * FROM llm_connections WHERE purpose = 'embedding'").fetchone()
        assert row["base_url"] == "http://old-emb"
        assert row["model"] == "emb-model"


class TestMigrateAddMultiBackendSupport:

    def test_adds_is_active_and_marks_existing_rows_active(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        conn = get_conn()
        conn.executescript(
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
            );
            INSERT INTO llm_connections (purpose, backend_type, base_url, api_key, model, params, created_at, updated_at)
                VALUES ('reranking', 'openai', 'http://old-rrk', 'k', 'rrk-model', '{}', 100, 100);
            """
        )
        conn.commit()

        repo = LLMSettingsRepository(get_conn, lock)
        repo.initialize(Settings())

        cols = {r["name"] for r in conn.execute("PRAGMA table_info(llm_connections)").fetchall()}
        assert "is_active" in cols
        row = conn.execute("SELECT * FROM llm_connections WHERE purpose = 'reranking'").fetchone()
        assert row["is_active"] == 1
        assert row["base_url"] == "http://old-rrk"

        # UNIQUE(purpose) must be gone -- a purpose can now have multiple connections
        conn.execute(
            "INSERT INTO llm_connections (purpose, backend_type, base_url, model, params, is_active, "
            "compaction_enabled, created_at, updated_at) VALUES ('reranking', 'ollama', 'http://second', '', '{}', 0, 0, 2, 2)"
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) AS c FROM llm_connections WHERE purpose = 'reranking'").fetchone()["c"]
        assert count == 2


class TestMigrateAddCompactionColumns:

    def test_adds_compaction_columns_defaulting_to_disabled(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        conn = get_conn()
        conn.executescript(
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
            );
            INSERT INTO llm_connections (purpose, backend_type, base_url, api_key, model, params, is_active, created_at, updated_at)
                VALUES ('generation', 'openai', 'http://old-gen', 'k', 'gen-model', '{}', 1, 100, 100);
            """
        )
        conn.commit()

        repo = LLMSettingsRepository(get_conn, lock)
        repo.initialize(Settings())

        cols = {r["name"] for r in conn.execute("PRAGMA table_info(llm_connections)").fetchall()}
        assert {"compaction_enabled", "compaction_model", "compaction_context_window", "compaction_summary_length"} <= cols
        row = conn.execute("SELECT * FROM llm_connections WHERE purpose = 'generation'").fetchone()
        assert row["compaction_enabled"] == 0
        assert row["base_url"] == "http://old-gen"  # pre-existing data untouched


class TestInitializeFreshInstall:

    def test_seeds_one_connection_per_purpose_from_settings(self, repo):
        conns = repo.list_connections()
        purposes = {c["purpose"] for c in conns}
        assert purposes == {"generation", "embedding", "reranking", "vector_db"}

    def test_does_not_reseed_once_any_connection_exists(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        repo = LLMSettingsRepository(get_conn, lock)
        repo.initialize(Settings())
        repo.delete_connection(connection_id=repo.list_connections()[0]["id"])
        remaining = len(repo.list_connections())

        repo.initialize(Settings())  # re-running initialize must not resurrect the deleted row

        assert len(repo.list_connections()) == remaining


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

class TestListAndGetConnections:

    def test_list_connections_masks_api_key(self, repo):
        for c in repo.list_connections():
            assert "api_key" not in c
            assert "has_api_key" in c

    def test_get_connection_includes_raw_api_key(self, repo):
        gen = next(c for c in repo.list_connections() if c["purpose"] == "generation")
        full = repo.get_connection(gen["id"])
        assert "api_key" in full

    def test_get_connection_returns_none_for_missing_id(self, repo):
        assert repo.get_connection(999999) is None

    def test_get_connection_by_purpose_returns_only_active(self, repo):
        gen = next(c for c in repo.list_connections() if c["purpose"] == "generation")
        second_id = repo.create_connection(purpose="generation", backend_type="ollama", base_url="http://b", api_key=None)
        active = repo.get_connection_by_purpose("generation")
        assert active["id"] == gen["id"]  # the original seeded row, not the new inactive one
        assert second_id != gen["id"]


class TestCreateConnection:

    def test_first_connection_for_a_purpose_activates_itself(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        repo = LLMSettingsRepository(get_conn, lock)
        repo.initialize(Settings())
        for c in repo.list_connections():
            repo.delete_connection(connection_id=c["id"])

        cid = repo.create_connection(purpose="generation", backend_type="openai", base_url="http://x", api_key="k")

        assert repo.get_connection(cid)["is_active"] is True

    def test_second_connection_for_a_purpose_starts_inactive(self, repo):
        cid = repo.create_connection(purpose="generation", backend_type="ollama", base_url="http://x", api_key=None)
        assert repo.get_connection(cid)["is_active"] is False


class TestActivateConnection:

    def test_activating_one_deactivates_its_siblings(self, repo):
        original = next(c for c in repo.list_connections() if c["purpose"] == "generation")
        new_id = repo.create_connection(purpose="generation", backend_type="ollama", base_url="http://b", api_key=None)

        repo.activate_connection(connection_id=new_id)

        assert repo.get_connection(new_id)["is_active"] is True
        assert repo.get_connection(original["id"])["is_active"] is False

    def test_raises_value_error_for_unknown_connection(self, repo):
        with pytest.raises(ValueError):
            repo.activate_connection(connection_id=999999)


class TestUpdateConnection:

    def test_updates_fields_and_replaces_api_key_when_given(self, repo):
        gen = next(c for c in repo.list_connections() if c["purpose"] == "generation")
        repo.update_connection(
            connection_id=gen["id"], base_url="http://updated", api_key="newkey",
            model="new-model", params={"temperature": 0.9},
        )
        full = repo.get_connection(gen["id"])
        assert full["base_url"] == "http://updated"
        assert full["api_key"] == "newkey"
        assert full["model"] == "new-model"
        assert full["params"] == {"temperature": 0.9}

    def test_blank_api_key_keeps_existing_value(self, repo):
        gen = next(c for c in repo.list_connections() if c["purpose"] == "generation")
        repo.update_connection(connection_id=gen["id"], base_url="http://x", api_key="realkey", model="m", params={})
        repo.update_connection(connection_id=gen["id"], base_url="http://y", api_key=None, model="m2", params={})
        full = repo.get_connection(gen["id"])
        assert full["api_key"] == "realkey"  # untouched by the second (blank-api_key) update
        assert full["base_url"] == "http://y"

    def test_updates_compaction_settings(self, repo):
        gen = next(c for c in repo.list_connections() if c["purpose"] == "generation")
        repo.update_connection(
            connection_id=gen["id"], base_url="http://x", api_key="k", model="m", params={},
            compaction_enabled=True, compaction_model="cm", compaction_context_window=8000, compaction_summary_length=500,
        )
        full = repo.get_connection(gen["id"])
        assert full["compaction_enabled"] is True
        assert full["compaction_model"] == "cm"
        assert full["compaction_context_window"] == 8000


class TestDeleteConnection:

    def test_removes_the_row(self, repo):
        gen = next(c for c in repo.list_connections() if c["purpose"] == "generation")
        repo.delete_connection(connection_id=gen["id"])
        assert repo.get_connection(gen["id"]) is None
