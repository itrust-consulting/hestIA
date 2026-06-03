from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from hestia.infrastructure.logging.audit import AuditLogger


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
        assert extra["target"] == "user-uuid"
