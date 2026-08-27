from __future__ import annotations

import logging

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
    ) -> None:
        _log.info("ai_response", extra={
            "user_id": user_id,
            "exec_type": exec_type,
            "response_len": response_len,
            "latency_ms": latency_ms,
        })

    def admin_action(
        self,
        *,
        actor_id: str,
        action: str,
        target: str,
        detail: dict | None = None,
    ) -> None:
        _log.info("admin_action", extra={
            "actor_id": actor_id,
            "action": action,
            "target": target,
            "detail": detail,
        })


audit = AuditLogger()
