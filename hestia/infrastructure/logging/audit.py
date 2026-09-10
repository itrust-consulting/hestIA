from __future__ import annotations

import logging
from contextlib import contextmanager

_log = logging.getLogger("hestia.audit")


# @MRS-064, @MRS-068
class AuditLogger:
    """
    Typed facade over the hestia.audit logger.

    Every method corresponds to one auditable event class.
    The msg field names the event; extra fields carry structured data.
    Raw prompt/response content is never logged here — only metadata.
    """

    def auth_attempt(
        self,
        *,
        username: str,
        success: bool,
        source: str,
        reason: str | None = None,
        ip: str | None = None,
    ) -> None:
        _log.info("auth_attempt", extra={
            "username": username,
            "success": success,
            "source": source,
            "reason": reason,
            "ip": ip,
        })

    def logout(
        self,
        *,
        user_id: str,
        username: str,
        source: str,
    ) -> None:
        _log.info("logout", extra={
            "user_id": user_id,
            "username": username,
            "source": source,
        })

    def policy_decision(
        self,
        *,
        user_id: str,
        exec_type: str,
        collection: str | None,
        decision: str,
        reason: str | None = None,
    ) -> None:
        _log.info("policy_decision", extra={
            "user_id": user_id,
            "exec_type": exec_type,
            "collection": collection,
            "decision": decision,
            "reason": reason,
        })

    def ai_request(
        self,
        *,
        user_id: str,
        exec_type: str,
        model: str | None,
        collection: str | None,
        prompt_len: int,
        stream: bool,
    ) -> None:
        _log.info("ai_request", extra={
            "user_id": user_id,
            "exec_type": exec_type,
            "model": model,
            "collection": collection,
            "prompt_len": prompt_len,
            "stream": stream,
        })

    def ai_response(
        self,
        *,
        user_id: str,
        exec_type: str,
        response_len: int,
        latency_ms: float,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        _log.info("ai_response", extra={
            "user_id": user_id,
            "exec_type": exec_type,
            "response_len": response_len,
            "latency_ms": latency_ms,
            "success": success,
            "error": error,
        })

    def admin_action(
        self,
        *,
        actor_id: str,
        action: str,
        target: str,
        detail: dict | None = None,
        success: bool = True,
        reason: str | None = None,
    ) -> None:
        _log.info("admin_action", extra={
            "actor_id": actor_id,
            "action": action,
            "target": target,
            "detail": detail,
            "success": success,
            "reason": reason,
        })

    def user_action(
        self,
        *,
        actor_id: str,
        action: str,
        target: str | None = None,
        success: bool = True,
        reason: str | None = None,
    ) -> None:
        _log.info("user_action", extra={
            "actor_id": actor_id,
            "action": action,
            "target": target,
            "success": success,
            "reason": reason,
        })

    def access_denied(
        self,
        *,
        actor_id: str,
        action: str,
        target: str | None = None,
        reason: str | None = None,
    ) -> None:
        _log.info("access_denied", extra={
            "actor_id": actor_id,
            "action": action,
            "target": target,
            "reason": reason,
        })

    def data_action(
        self,
        *,
        actor_id: str,
        action: str,
        target: str,
        detail: dict | None = None,
        success: bool = True,
        reason: str | None = None,
    ) -> None:
        _log.info("data_action", extra={
            "actor_id": actor_id,
            "action": action,
            "target": target,
            "detail": detail,
            "success": success,
            "reason": reason,
        })

    def connection_action(
        self,
        *,
        actor_id: str,
        action: str,
        target: str,
        detail: dict | None = None,
        success: bool = True,
        reason: str | None = None,
    ) -> None:
        _log.info("connection_action", extra={
            "actor_id": actor_id,
            "action": action,
            "target": target,
            "detail": detail,
            "success": success,
            "reason": reason,
        })


audit = AuditLogger()


@contextmanager
def audited(log_fn, **kwargs):
    """Wraps a mutation with a call to one of AuditLogger's action methods on
    both outcomes: success=True after the block completes, success=False
    (with the exception's message as reason) if it raises. Re-raises so
    route-level error handling (HestiaError -> HTTP status mapping) is
    unaffected. log_fn is one of audit.admin_action / data_action /
    user_action; kwargs are forwarded as-is (actor_id, action, target,
    detail, ...) to both the success and failure calls."""
    try:
        yield
    except Exception as e:
        log_fn(success=False, reason=str(e), **kwargs)
        raise
    else:
        log_fn(success=True, **kwargs)
