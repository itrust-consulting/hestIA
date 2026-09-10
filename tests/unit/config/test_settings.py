from __future__ import annotations

import json
import pytest

from hestia.config.settings import (
    _parse_ldap_group_mapping,
    _parse_list,
    _parse_set,
    _parse_str_mapping,
    _load_auth_settings,
    Settings,
)
from hestia.domain.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# Settings.insecure_llm_urls
# ---------------------------------------------------------------------------

class TestInsecureLlmUrls:

    def test_https_urls_are_not_flagged(self):
        s = Settings(llm_url="https://llm.example.com", emb_url="https://llm.example.com",
                      rrk_url="https://llm.example.com")
        assert s.insecure_llm_urls() == []

    def test_localhost_http_is_not_flagged(self):
        s = Settings(llm_url="http://localhost:8000", emb_url="http://127.0.0.1:8000",
                      rrk_url="http://localhost:8000")
        assert s.insecure_llm_urls() == []

    def test_non_local_http_is_flagged(self):
        s = Settings(llm_url="http://llm.internal:8000", emb_url="https://llm.example.com",
                      rrk_url="https://llm.example.com")
        assert s.insecure_llm_urls() == [("llm_url", "http://llm.internal:8000")]

    def test_multiple_insecure_urls_all_reported(self):
        s = Settings(llm_url="http://a.internal", emb_url="http://b.internal",
                      rrk_url="https://c.example.com")
        assert s.insecure_llm_urls() == [
            ("llm_url", "http://a.internal"), ("emb_url", "http://b.internal"),
        ]


# ---------------------------------------------------------------------------
# _parse_str_mapping
# ---------------------------------------------------------------------------

class TestParseStrMapping:

    def test_returns_none_for_empty(self):
        assert _parse_str_mapping(None) is None
        assert _parse_str_mapping("") is None

    def test_parses_valid_json_object(self):
        raw = json.dumps({"orgA": "tenantA", "orgB": "tenantB"})
        result = _parse_str_mapping(raw)
        assert result == {"orgA": "tenantA", "orgB": "tenantB"}

    def test_raises_on_non_dict_json(self):
        with pytest.raises(ConfigurationError):
            _parse_str_mapping(json.dumps(["a", "b"]))


# ---------------------------------------------------------------------------
# _parse_ldap_group_mapping
# ---------------------------------------------------------------------------

class TestParseLdapGroupMapping:

    def test_returns_none_for_empty(self):
        assert _parse_ldap_group_mapping(None) is None
        assert _parse_ldap_group_mapping("") is None

    def test_lowercases_keys(self):
        raw = json.dumps({"HestiaAdmin": ["admin"], "HestiaUser": ["user"]})
        result = _parse_ldap_group_mapping(raw)
        assert "hestiaadmin" in result
        assert "hestiauser" in result

    def test_preserves_values(self):
        raw = json.dumps({"grp": ["admin", "user"]})
        result = _parse_ldap_group_mapping(raw)
        assert result["grp"] == ["admin", "user"]

    def test_raises_on_non_dict_json(self):
        with pytest.raises(ConfigurationError):
            _parse_ldap_group_mapping(json.dumps(["a", "b"]))


# ---------------------------------------------------------------------------
# _parse_set
# ---------------------------------------------------------------------------

class TestParseSet:

    def test_returns_none_for_empty(self):
        assert _parse_set(None) is None
        assert _parse_set("") is None

    def test_splits_comma_separated(self):
        result = _parse_set("groupA,groupB,groupC")
        assert result == {"groupa", "groupb", "groupc"}

    def test_strips_whitespace(self):
        result = _parse_set("  a , b , c  ")
        assert result == {"a", "b", "c"}

    def test_ignores_empty_segments(self):
        result = _parse_set("a,,b,")
        assert result == {"a", "b"}


# ---------------------------------------------------------------------------
# _parse_list
# ---------------------------------------------------------------------------

class TestParseList:

    def test_returns_empty_list_for_none(self):
        assert _parse_list(None) == []
        assert _parse_list("") == []

    def test_splits_comma_separated(self):
        result = _parse_list("openid,profile,email")
        assert result == ["openid", "profile", "email"]

    def test_strips_whitespace(self):
        result = _parse_list("  a , b , c  ")
        assert result == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# _load_auth_settings
# ---------------------------------------------------------------------------

class TestLoadAuthSettings:

    def test_raises_on_missing_secret_key(self, monkeypatch):
        monkeypatch.setenv("AUTH_SECRET_KEY", "")
        with pytest.raises(ConfigurationError, match="AUTH_SECRET_KEY"):
            _load_auth_settings()

    def test_raises_when_key_too_short(self, monkeypatch):
        monkeypatch.setenv("AUTH_SECRET_KEY", "tooshort")
        with pytest.raises(ConfigurationError, match="32 characters"):
            _load_auth_settings()

    def test_succeeds_with_long_enough_key(self, monkeypatch):
        monkeypatch.setenv("AUTH_SECRET_KEY", "a" * 32)
        settings = _load_auth_settings()
        assert settings.token_secret_key == "a" * 32

    def test_audit_logs_default_false(self, monkeypatch):
        monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 32)
        monkeypatch.delenv("AUTH_AUDIT_LOGS", raising=False)
        settings = _load_auth_settings()
        assert settings.audit_logs is False

    def test_ip_rate_limit_defaults(self, monkeypatch):
        monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 32)
        monkeypatch.delenv("AUTH_IP_RATE_LIMIT_ATTEMPTS", raising=False)
        monkeypatch.delenv("AUTH_IP_RATE_LIMIT_WINDOW_MINUTES", raising=False)
        settings = _load_auth_settings()
        assert settings.ip_rate_limit_max_attempts == 30
        assert settings.ip_rate_limit_window_minutes == 1

    def test_ip_rate_limit_reads_env_overrides(self, monkeypatch):
        monkeypatch.setenv("AUTH_SECRET_KEY", "x" * 32)
        monkeypatch.setenv("AUTH_IP_RATE_LIMIT_ATTEMPTS", "50")
        monkeypatch.setenv("AUTH_IP_RATE_LIMIT_WINDOW_MINUTES", "2")
        settings = _load_auth_settings()
        assert settings.ip_rate_limit_max_attempts == 50
        assert settings.ip_rate_limit_window_minutes == 2


# ---------------------------------------------------------------------------
# Settings.load
# ---------------------------------------------------------------------------

class TestSettingsLoad:

    def test_assembles_with_defaults(self, monkeypatch):
        monkeypatch.setenv("AUTH_SECRET_KEY", "k" * 32)
        monkeypatch.setenv("DEFAULT_GEN_MODEL", "default-model")
        s = Settings.load()
        assert s.auth is not None
        assert s.auth.auth_mode == "local"

    def test_port_parsed_from_env(self, monkeypatch):
        monkeypatch.setenv("PORT", "9999")
        monkeypatch.setenv("AUTH_SECRET_KEY", "k" * 32)
        monkeypatch.setenv("DEFAULT_GEN_MODEL", "m")
        s = Settings.load()
        assert s.port == 9999

    def test_raises_when_model_env_var_missing(self, monkeypatch):
        monkeypatch.delenv("DEFAULT_GEN_MODEL", raising=False)
        monkeypatch.setenv("AUTH_SECRET_KEY", "k" * 32)
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            Settings.load()

    def test_raises_when_auth_secret_key_missing(self, monkeypatch):
        monkeypatch.delenv("AUTH_SECRET_KEY", raising=False)
        monkeypatch.setenv("DEFAULT_GEN_MODEL", "m")
        with pytest.raises(ConfigurationError, match="AUTH_SECRET_KEY"):
            Settings.load()

    def test_bootstrap_admin_defaults_to_none(self, monkeypatch):
        monkeypatch.delenv("DEFAULT_ADMIN_USERNAME", raising=False)
        monkeypatch.delenv("DEFAULT_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("DEFAULT_ADMIN_EMAIL", raising=False)
        monkeypatch.setenv("AUTH_SECRET_KEY", "k" * 32)
        monkeypatch.setenv("DEFAULT_GEN_MODEL", "m")
        s = Settings.load()
        assert s.bootstrap_admin_username is None
        assert s.bootstrap_admin_password is None
        assert s.bootstrap_admin_email is None
        assert s.bootstrap_admin_first_name == "Admin"
        assert s.bootstrap_admin_last_name == "User"

    def test_bootstrap_admin_loaded_from_env(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_ADMIN_USERNAME", "root")
        monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "a" * 20)
        monkeypatch.setenv("DEFAULT_ADMIN_EMAIL", "root@example.com")
        monkeypatch.setenv("DEFAULT_ADMIN_FIRST_NAME", "Root")
        monkeypatch.setenv("DEFAULT_ADMIN_LAST_NAME", "Account")
        monkeypatch.setenv("AUTH_SECRET_KEY", "k" * 32)
        monkeypatch.setenv("DEFAULT_GEN_MODEL", "m")
        s = Settings.load()
        assert s.bootstrap_admin_username == "root"
        assert s.bootstrap_admin_password == "a" * 20
        assert s.bootstrap_admin_email == "root@example.com"
        assert s.bootstrap_admin_first_name == "Root"
        assert s.bootstrap_admin_last_name == "Account"
