from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from hestia.config.settings import AuthSettings, LDAPSettings, OIDCSettings
from hestia.infrastructure.db.auth_settings_repository import AuthSettingsRepository
from hestia.infrastructure.db.user_repository import create_sqlite_connection


# ---------------------------------------------------------------------------
# Fixtures — in-memory SQLite
# ---------------------------------------------------------------------------

def _settings(**auth_overrides):
    auth_overrides.setdefault("token_secret_key", "x" * 32)
    return SimpleNamespace(
        auth=AuthSettings(**auth_overrides),
        oidc=None,
        ldap=None,
    )


@pytest.fixture
def repo():
    get_conn, close, lock = create_sqlite_connection(":memory:")
    r = AuthSettingsRepository(get_conn=get_conn, db_lock=lock)
    r.initialize(_settings())
    return r


# ---------------------------------------------------------------------------
# initialize (schema creation + seed-once)
# ---------------------------------------------------------------------------

class TestInitialize:

    def test_creates_auth_settings_table(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = AuthSettingsRepository(get_conn=get_conn, db_lock=lock)
        r.initialize(_settings())
        conn = get_conn()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "auth_settings" in tables

    def test_seeds_row_from_settings_on_fresh_install(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = AuthSettingsRepository(get_conn=get_conn, db_lock=lock)
        r.initialize(_settings(auth_mode="local", password_min_length=12, token_secret_key="s" * 32))
        row = r.get_settings()
        assert row is not None
        assert row["auth_mode"] == "local"
        assert row["password_min_length"] == 12
        assert row["token_secret_key"] == "s" * 32

    def test_seeds_oidc_and_ldap_when_present(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = AuthSettingsRepository(get_conn=get_conn, db_lock=lock)
        settings = SimpleNamespace(
            auth=AuthSettings(auth_mode="oidc", token_secret_key="x" * 32),
            oidc=OIDCSettings(provider_url="https://idp.example.com", client_id="cid", scopes=["openid", "email"]),
            ldap=LDAPSettings(host="ldap.example.com", allowed_groups={"admins", "users"}),
        )
        r.initialize(settings)
        row = r.get_settings()
        assert row["oidc_provider_url"] == "https://idp.example.com"
        assert row["oidc_client_id"] == "cid"
        assert set(row["oidc_scopes"]) == {"openid", "email"}
        assert row["ldap_host"] == "ldap.example.com"
        assert set(row["ldap_allowed_groups"]) == {"admins", "users"}

    def test_does_not_reseed_once_row_exists(self):
        # An admin may have intentionally changed the row -- re-running
        # initialize() (e.g. on a restart) must not clobber their edit.
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = AuthSettingsRepository(get_conn=get_conn, db_lock=lock)
        r.initialize(_settings(auth_mode="local"))
        r.update_settings(auth_mode="ldap")

        r.initialize(_settings(auth_mode="local"))  # simulate a restart
        row = r.get_settings()
        assert row["auth_mode"] == "ldap"

    def test_null_json_fields_stay_none(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = AuthSettingsRepository(get_conn=get_conn, db_lock=lock)
        r.initialize(_settings(ldap_group_mapping=None))
        row = r.get_settings()
        assert row["ldap_group_mapping"] is None


# ---------------------------------------------------------------------------
# get_settings
# ---------------------------------------------------------------------------

class TestGetSettings:

    def test_returns_none_when_no_row(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = AuthSettingsRepository(get_conn=get_conn, db_lock=lock)
        conn = get_conn()
        conn.executescript(
            """
            CREATE TABLE auth_settings (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              auth_mode TEXT NOT NULL,
              password_min_length INTEGER NOT NULL,
              max_failed_attempts INTEGER NOT NULL,
              lockout_duration_minutes INTEGER NOT NULL,
              token_secret_key TEXT NOT NULL,
              token_encoding_alg TEXT NOT NULL,
              token_lifetime_minutes INTEGER NOT NULL,
              audit_logs INTEGER NOT NULL DEFAULT 0,
              ldap_group_mapping TEXT,
              oidc_provider_url TEXT NOT NULL DEFAULT '',
              oidc_client_id TEXT NOT NULL DEFAULT '',
              oidc_client_secret TEXT NOT NULL DEFAULT '',
              oidc_scopes TEXT NOT NULL DEFAULT '[]',
              oidc_role_claim TEXT NOT NULL DEFAULT 'roles',
              oidc_role_mapping TEXT,
              oidc_org_claim TEXT NOT NULL DEFAULT 'organization',
              oidc_org_mapping TEXT,
              ldap_host TEXT NOT NULL DEFAULT '',
              ldap_port INTEGER NOT NULL DEFAULT 636,
              ldap_search_base TEXT NOT NULL DEFAULT '',
              ldap_user_attribute TEXT NOT NULL DEFAULT 'uid',
              ldap_mail_attribute TEXT NOT NULL DEFAULT 'mail',
              ldap_use_ssl INTEGER NOT NULL DEFAULT 1,
              ldap_validate_cert INTEGER NOT NULL DEFAULT 1,
              ldap_bind_dn TEXT,
              ldap_bind_password TEXT,
              ldap_user_dn_template TEXT,
              ldap_allowed_groups TEXT,
              ldap_mode TEXT NOT NULL DEFAULT 'auto',
              updated_at INTEGER NOT NULL
            );
            """
        )
        conn.commit()
        assert r.get_settings() is None

    def test_bool_and_json_fields_decoded(self, repo):
        row = repo.get_settings()
        assert isinstance(row["audit_logs"], bool)
        assert isinstance(row["ldap_use_ssl"], bool)
        assert isinstance(row["ldap_validate_cert"], bool)
        assert row["oidc_scopes"] == ["openid", "profile", "email"]


# ---------------------------------------------------------------------------
# update_settings -- partial update semantics
# ---------------------------------------------------------------------------

class TestUpdateSettings:

    def test_updates_only_passed_fields(self, repo):
        before = repo.get_settings()
        repo.update_settings(auth_mode="ldap")
        after = repo.get_settings()
        assert after["auth_mode"] == "ldap"
        assert after["password_min_length"] == before["password_min_length"]

    def test_bumps_updated_at(self, repo):
        before = repo.get_settings()
        repo.update_settings(auth_mode="ldap")
        after = repo.get_settings()
        assert after["updated_at"] >= before["updated_at"]

    def test_no_fields_is_a_noop(self, repo):
        before = repo.get_settings()
        repo.update_settings()
        after = repo.get_settings()
        assert after == before

    def test_json_field_round_trips(self, repo):
        repo.update_settings(ldap_group_mapping={"admins": ["role1", "role2"]})
        row = repo.get_settings()
        assert row["ldap_group_mapping"] == {"admins": ["role1", "role2"]}

    def test_json_field_set_to_none_clears_it(self, repo):
        repo.update_settings(ldap_group_mapping={"admins": ["role1"]})
        repo.update_settings(ldap_group_mapping=None)
        row = repo.get_settings()
        assert row["ldap_group_mapping"] is None

    def test_bool_field_stored_as_int_and_read_back_as_bool(self, repo):
        repo.update_settings(audit_logs=True)
        row = repo.get_settings()
        assert row["audit_logs"] is True
        repo.update_settings(audit_logs=False)
        row = repo.get_settings()
        assert row["audit_logs"] is False

    @pytest.mark.parametrize("field", ["token_secret_key", "oidc_client_secret", "ldap_bind_password"])
    def test_secret_field_none_keeps_existing_value(self, repo, field):
        repo.update_settings(**{field: "original-secret-value"})
        before = repo.get_settings()[field]

        # blank/omitted (None) means "keep existing" -- must not overwrite.
        repo.update_settings(**{field: None, "auth_mode": "ldap"})
        after = repo.get_settings()

        assert after[field] == before
        assert after["auth_mode"] == "ldap"  # the other field in the same call still applies

    @pytest.mark.parametrize("field", ["token_secret_key", "oidc_client_secret", "ldap_bind_password"])
    def test_secret_field_non_none_overwrites(self, repo, field):
        repo.update_settings(**{field: "brand-new-secret-value"})
        row = repo.get_settings()
        assert row[field] == "brand-new-secret-value"

    def test_updating_multiple_fields_at_once(self, repo):
        repo.update_settings(
            auth_mode="oidc",
            oidc_provider_url="https://idp.example.com",
            oidc_client_id="my-client",
            oidc_scopes=["openid"],
            password_min_length=20,
        )
        row = repo.get_settings()
        assert row["auth_mode"] == "oidc"
        assert row["oidc_provider_url"] == "https://idp.example.com"
        assert row["oidc_client_id"] == "my-client"
        assert row["oidc_scopes"] == ["openid"]
        assert row["password_min_length"] == 20
