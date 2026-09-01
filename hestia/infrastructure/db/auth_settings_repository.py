from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any, Dict, Optional

from hestia.config.settings import LDAPSettings, OIDCSettings, Settings
from hestia.infrastructure.db.user_repository import with_txn

# Secret columns get "blank/omitted means keep existing" semantics in
# update_settings -- never overwritten unless the caller passes a non-None
# value for them.
_SECRET_FIELDS = ("token_secret_key", "oidc_client_secret", "ldap_bind_password")

_JSON_FIELDS = (
    "ldap_group_mapping", "oidc_scopes", "oidc_role_mapping", "oidc_org_mapping", "ldap_allowed_groups",
)

_BOOL_FIELDS = ("ldap_use_ssl", "ldap_validate_cert", "audit_logs")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    d = dict(r)
    for field in _JSON_FIELDS:
        d[field] = json.loads(d[field]) if d[field] is not None else None
    for field in _BOOL_FIELDS:
        d[field] = bool(d[field])
    return d


class AuthSettingsRepository:
    """Global authentication config (mode, password policy, JWT signing,
    OIDC, LDAP) -- a single row (id=1), seeded once on a genuinely fresh
    install from env-var Settings, then DB is the source of truth. Mirrors
    LLMSettingsRepository's seed-once-then-DB-owns-it pattern; unlike LLM
    connections there is exactly one row (auth config is global, not
    per-purpose), so no active-flag/multi-row bookkeeping is needed."""

    def __init__(self, get_conn: callable, db_lock: threading.Lock):
        self._get_conn = get_conn
        self._db_lock = db_lock

    @with_txn
    def initialize(self, conn: sqlite3.Connection, settings: Settings) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_settings (
              id                         INTEGER PRIMARY KEY CHECK (id = 1),
              auth_mode                  TEXT NOT NULL CHECK (auth_mode IN ('local','ldap','oidc')),
              password_min_length        INTEGER NOT NULL,
              max_failed_attempts        INTEGER NOT NULL,
              lockout_duration_minutes   INTEGER NOT NULL,
              token_secret_key           TEXT NOT NULL,
              token_encoding_alg         TEXT NOT NULL,
              token_lifetime_minutes     INTEGER NOT NULL,
              audit_logs                 INTEGER NOT NULL DEFAULT 0,
              ldap_group_mapping         TEXT,
              oidc_provider_url          TEXT NOT NULL DEFAULT '',
              oidc_client_id             TEXT NOT NULL DEFAULT '',
              oidc_client_secret         TEXT NOT NULL DEFAULT '',
              oidc_scopes                TEXT NOT NULL DEFAULT '[]',
              oidc_role_claim            TEXT NOT NULL DEFAULT 'roles',
              oidc_role_mapping          TEXT,
              oidc_org_claim             TEXT NOT NULL DEFAULT 'organization',
              oidc_org_mapping           TEXT,
              ldap_host                  TEXT NOT NULL DEFAULT '',
              ldap_port                  INTEGER NOT NULL DEFAULT 636,
              ldap_search_base           TEXT NOT NULL DEFAULT '',
              ldap_user_attribute        TEXT NOT NULL DEFAULT 'uid',
              ldap_mail_attribute        TEXT NOT NULL DEFAULT 'mail',
              ldap_use_ssl               INTEGER NOT NULL DEFAULT 1,
              ldap_validate_cert         INTEGER NOT NULL DEFAULT 1,
              ldap_bind_dn               TEXT,
              ldap_bind_password         TEXT,
              ldap_user_dn_template      TEXT,
              ldap_allowed_groups        TEXT,
              ldap_mode                  TEXT NOT NULL DEFAULT 'auto',
              updated_at                 INTEGER NOT NULL
            );
            """
        )

        # Only seed on a genuinely fresh install -- once the row exists, an
        # admin may have intentionally changed it, and re-seeding on every
        # startup would silently discard their edits.
        has_row = conn.execute("SELECT 1 FROM auth_settings WHERE id = 1").fetchone()
        if has_row:
            return

        auth = settings.auth
        oidc = settings.oidc or OIDCSettings()
        ldap = settings.ldap or LDAPSettings()
        if auth is None:
            return  # enable_auth is False -- nothing to seed; this page is unreachable anyway (no login).

        conn.execute(
            """
            INSERT INTO auth_settings (
              id, auth_mode, password_min_length, max_failed_attempts, lockout_duration_minutes,
              token_secret_key, token_encoding_alg, token_lifetime_minutes, audit_logs, ldap_group_mapping,
              oidc_provider_url, oidc_client_id, oidc_client_secret, oidc_scopes, oidc_role_claim,
              oidc_role_mapping, oidc_org_claim, oidc_org_mapping,
              ldap_host, ldap_port, ldap_search_base, ldap_user_attribute, ldap_mail_attribute,
              ldap_use_ssl, ldap_validate_cert, ldap_bind_dn, ldap_bind_password, ldap_user_dn_template,
              ldap_allowed_groups, ldap_mode, updated_at
            ) VALUES (
              1, ?, ?, ?, ?,
              ?, ?, ?, ?, ?,
              ?, ?, ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?, ?, ?,
              ?, ?, ?, ?, ?,
              ?, ?, ?
            )
            """,
            (
                auth.auth_mode, auth.password_min_length, auth.max_failed_attempts, auth.lockout_duration_minutes,
                auth.token_secret_key, auth.token_encoding_alg, auth.token_lifetime_minutes, int(auth.audit_logs),
                json.dumps(auth.ldap_group_mapping) if auth.ldap_group_mapping is not None else None,
                oidc.provider_url, oidc.client_id, oidc.client_secret, json.dumps(oidc.scopes), oidc.role_claim,
                json.dumps(oidc.role_mapping) if oidc.role_mapping is not None else None,
                oidc.org_claim,
                json.dumps(oidc.org_mapping) if oidc.org_mapping is not None else None,
                ldap.host, ldap.port, ldap.search_base, ldap.user_attribute, ldap.mail_attribute,
                int(ldap.use_ssl), int(ldap.validate_cert), ldap.bind_dn, ldap.bind_password, ldap.user_dn_template,
                json.dumps(sorted(ldap.allowed_groups)) if ldap.allowed_groups is not None else None,
                ldap.mode, _now_ms(),
            ),
        )

    def get_settings(self) -> Optional[Dict[str, Any]]:
        r = self._get_conn().execute("SELECT * FROM auth_settings WHERE id = 1").fetchone()
        return _row_to_dict(r) if r else None

    @with_txn
    def update_settings(self, conn: sqlite3.Connection, **fields: Any) -> None:
        """Partial update -- only columns present (and non-None, for the
        three secret fields) in `fields` are written. `fields` uses the same
        keys as the auth_settings columns."""
        set_clauses = []
        values = []
        for key, value in fields.items():
            if key in _SECRET_FIELDS and value is None:
                continue  # blank/omitted secret means "keep existing"
            if key in _JSON_FIELDS:
                value = json.dumps(value) if value is not None else None
            elif key in _BOOL_FIELDS and value is not None:
                value = int(value)
            set_clauses.append(f"{key} = ?")
            values.append(value)
        if not set_clauses:
            return
        set_clauses.append("updated_at = ?")
        values.append(_now_ms())
        conn.execute(f"UPDATE auth_settings SET {', '.join(set_clauses)} WHERE id = 1", values)
