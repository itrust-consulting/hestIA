"""TST-037 - Access and modification audit logging (SRS-027).

Expected outcome (the API-testable subset - the code-review portions of
SRS-027/TST-039 are covered separately by TST-076's design review):
1. Authentication events and administrative changes each produce a
   structured audit log entry.
2. Each audit entry records the acting user, action, resource, timestamp,
   and correlation ID.
4. An administrator can query the audit log via the API, filtered by log
   type and time range.
5. Access to the audit log query endpoint is restricted to administrators.

Log entry shape (confirmed against a live instance): every entry has fixed
fields ts/level/logger/request_id/msg, where `msg` is the *event type*
(e.g. "admin_action", "auth_attempt", "policy_decision"), not the specific
action - the specific action lives in a separate `action` field only present
on admin_action entries (e.g. action="user_create"). Earlier assertions in
this file incorrectly treated `msg` as if it carried the specific action.
"""
import time

from conftest import login


def test_admin_action_produces_audit_entry(admin_client, make_user):
    since = int(time.time()) - 5

    user = make_user()  # POST /admin/users/create -> msg="admin_action", action="user_create"

    time.sleep(1)  # give the async logging queue a moment to flush

    logs = admin_client.get("/admin/logs", params={"log_type": "audit", "since": since})
    assert logs.status_code == 200, logs.text
    entries = logs.json().get("entries", [])

    matches = [
        e for e in entries
        if e.get("msg") == "admin_action" and e.get("action") == "user_create" and e.get("target") == user.user_id
    ]
    assert matches, (
        f"expected an admin_action/user_create audit entry against "
        f"{user.user_id}, got entries: {entries}"
    )
    entry = matches[0]
    for field in ("ts", "level", "logger", "request_id", "msg"):
        assert field in entry, f"audit entry missing expected field {field!r}: {entry}"


def test_failed_login_produces_audit_entry(admin_client, make_user):
    """Login/logout events use msg="auth_attempt"/"logout" (hestia/infrastructure/
    logging/audit.py). Note: AuthSettings.audit_logs defaults to False
    (AUTH_AUDIT_LOGS env) - if the live instance hasn't explicitly enabled it,
    this correctly fails, documenting that gap against MRS-064/SRS-027 rather
    than a bug in this test."""
    since = int(time.time()) - 5
    user = make_user()

    from conftest import ApiClient
    login(ApiClient(), user.username, "definitely-wrong-password")

    time.sleep(1)

    logs = admin_client.get("/admin/logs", params={"log_type": "audit", "since": since})
    assert logs.status_code == 200, logs.text
    entries = logs.json().get("entries", [])
    matches = [e for e in entries if e.get("msg") == "auth_attempt" and e.get("success") is False]
    assert matches, (
        f"expected a failed auth_attempt audit entry for {user.username!r}; if none "
        f"appear at all, check whether AUTH_AUDIT_LOGS is enabled on this instance "
        f"(defaults to False). Entries seen: {entries}"
    )


def test_non_admin_denied_audit_log_access(make_user):
    user = make_user(roles=["user"])
    resp = user.login()
    assert resp.status_code == 200, resp.text

    denied = user.client.get("/admin/logs", params={"log_type": "audit"})
    assert denied.status_code == 403, (
        f"expected a non-admin to be denied audit log access, got "
        f"{denied.status_code}: {denied.text}"
    )


def test_audit_log_access_is_itself_audited(admin_client):
    """Per the original audit-logging investigation, log *export* (not the
    plain query) is the confirmed self-auditing action - GET /admin/logs
    alone was never confirmed to produce its own entry."""
    since = int(time.time()) - 5

    export = admin_client.get("/admin/logs/export", params={"log_type": "audit", "format": "ndjson"})
    assert export.status_code == 200, export.text
    time.sleep(1)

    logs = admin_client.get("/admin/logs", params={"log_type": "audit", "since": since})
    assert logs.status_code == 200, logs.text
    entries = logs.json().get("entries", [])
    matches = [
        e for e in entries
        if e.get("msg") == "admin_action" and "log" in str(e.get("action", "")).lower()
    ]
    assert matches, (
        f"expected the log-export action itself to be recorded as an audit "
        f"entry, got: {entries}"
    )
