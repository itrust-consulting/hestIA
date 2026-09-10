from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from hestia.infrastructure.logging.audit import AuditLogger, audited


@pytest.fixture
def logger():
    return AuditLogger()


class TestAuthAttempt:

    def test_calls_logger_info(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.auth_attempt(username="alice", success=True, source="local")
        mock_log.info.assert_called_once()
        msg, extra = mock_log.info.call_args[0][0], mock_log.info.call_args.kwargs.get("extra", {})
        assert msg == "auth_attempt"

    def test_includes_username_in_extra(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.auth_attempt(username="bob", success=False, source="ldap", reason="bad pw")
        extra = mock_log.info.call_args.kwargs["extra"]
        assert extra["username"] == "bob"
        assert extra["success"] is False
        assert extra["source"] == "ldap"


class TestPolicyDecision:

    def test_calls_logger_info(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.policy_decision(
                user_id="u1", exec_type="rag_chat", collection="col", decision="deny"
            )
        mock_log.info.assert_called_once()

    def test_extra_contains_decision(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.policy_decision(
                user_id="u1", exec_type="chat", collection=None, decision="allow"
            )
        extra = mock_log.info.call_args.kwargs["extra"]
        assert extra["decision"] == "allow"


class TestAiRequest:

    def test_logs_prompt_len(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.ai_request(
                user_id="u1", exec_type="generate", model="llama3",
                collection=None, prompt_len=42, stream=False,
            )
        extra = mock_log.info.call_args.kwargs["extra"]
        assert extra["prompt_len"] == 42


class TestAiResponse:

    def test_logs_latency(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.ai_response(user_id="u1", exec_type="chat", response_len=100, latency_ms=250.5)
        extra = mock_log.info.call_args.kwargs["extra"]
        assert extra["latency_ms"] == 250.5


class TestAdminAction:

    def test_logs_action_and_target(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.admin_action(actor_id="admin1", action="delete_user", target="user-uuid")
        extra = mock_log.info.call_args.kwargs["extra"]
        assert extra["action"] == "delete_user"


class TestConnectionAction:

    def test_logs_action_and_target(self, logger):
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.connection_action(actor_id="admin1", action="connection_create", target="5")
        extra = mock_log.info.call_args.kwargs["extra"]
        assert extra["action"] == "connection_create"
        assert extra["target"] == "5"
        assert extra["success"] is True
        assert extra["reason"] is None

    def test_supports_success_false_and_reason(self, logger):
        # Regression test: connection_action used to lack success/reason,
        # so llm_settings.py's connection mutations couldn't be wrapped in
        # audited() and a failure left no audit trail at all.
        with patch("hestia.infrastructure.logging.audit._log") as mock_log:
            logger.connection_action(
                actor_id="admin1", action="connection_delete", target="5",
                success=False, reason="boom",
            )
        extra = mock_log.info.call_args.kwargs["extra"]
        assert extra["success"] is False
        assert extra["reason"] == "boom"


class TestAudited:

    def test_success_calls_log_fn_with_success_true(self):
        log_fn = MagicMock()
        with audited(log_fn, actor_id="u1", action="thing_update", target="t1"):
            pass
        log_fn.assert_called_once_with(actor_id="u1", action="thing_update", target="t1", success=True)

    def test_failure_calls_log_fn_with_success_false_and_reraises(self):
        log_fn = MagicMock()
        with pytest.raises(ValueError):
            with audited(log_fn, actor_id="u1", action="thing_update", target="t1"):
                raise ValueError("x")
        log_fn.assert_called_once_with(
            actor_id="u1", action="thing_update", target="t1", success=False, reason="x"
        )

    def test_kwargs_without_target_or_detail_are_forwarded_as_given(self):
        # Mirrors account.py's usage of audit.user_action, which has no
        # detail parameter -- audited() must not assume every log_fn shares
        # admin_action/data_action's full signature.
        log_fn = MagicMock()
        with audited(log_fn, actor_id="u1", action="password_change"):
            pass
        log_fn.assert_called_once_with(actor_id="u1", action="password_change", success=True)
