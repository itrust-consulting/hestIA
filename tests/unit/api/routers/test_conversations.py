from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.conversations import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from tests.unit.conftest import _make_user


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


def _generator(chat_result=None):
    generator = MagicMock()
    generator.compaction_enabled = True
    generator.compaction_context_window = None
    generator.compaction_summary_length = None
    generator.compaction_model = None
    generator.default_model = "test-model"
    generator.chat = AsyncMock(return_value=chat_result)
    return generator


def _handler(users, generator=None, max_context_tokens=32000, summary_target_tokens=6000):
    handler = MagicMock()
    settings = MagicMock()
    settings.max_context_tokens = max_context_tokens
    settings.summary_target_tokens = summary_target_tokens
    settings.summary_model = None
    settings.default_gen_model = "test-model"
    handler.container.settings = settings
    handler.container.services.get.side_effect = lambda name: {"users": users, "generate": generator}.get(name)
    handler.container.require_service.side_effect = lambda name: {"users": users, "generate": generator}.get(name)
    return handler


def _users(tail, prior_summary=None):
    users = MagicMock()
    users.assert_conversation_owner = MagicMock()
    context_summary = (
        {"summary": prior_summary, "boundary_created_at": 0, "boundary_rowid": 0}
        if prior_summary
        else None
    )
    users.get_conversation_context_state.return_value = (
        {"context_summary": context_summary} if context_summary else {}
    )
    users.get_messages_after_boundary.return_value = tail
    return users


class TestGetConversationMessages:

    def test_first_page_includes_usage_fields(self):
        tail = [{"role": "user", "content": "hi", "created_at": 1, "rowid": 1}]
        users = _users(tail)
        users.get_conversation_messages.return_value = {
            "messages": [], "has_more": False, "next_cursor": None,
        }
        handler = _handler(users, _generator())

        client = TestClient(_app(handler=handler))
        resp = client.get(f"/conversations/{uuid.uuid4()}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["used_tokens"] > 0
        assert body["max_tokens"] == 32000
        assert body["needs_compaction"] is False

    def test_pagination_page_omits_usage_fields(self):
        users = _users(tail=[])
        users.get_conversation_messages.return_value = {
            "messages": [], "has_more": False, "next_cursor": None,
        }
        handler = _handler(users)

        client = TestClient(_app(handler=handler))
        resp = client.get(f"/conversations/{uuid.uuid4()}?before_created_at=5&before_rowid=5")

        assert resp.status_code == 200
        body = resp.json()
        assert body["used_tokens"] is None
        assert body["max_tokens"] is None
        assert body["needs_compaction"] is None
        users.get_messages_after_boundary.assert_not_called()


class TestCompactConversation:

    def test_not_needed_when_under_budget(self):
        tail = [{"role": "user", "content": "hi", "created_at": 1, "rowid": 1}]
        users = _users(tail)
        generator = _generator()
        handler = _handler(users, generator)

        client = TestClient(_app(handler=handler))
        resp = client.post(f"/conversations/{uuid.uuid4()}/compact")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_needed"
        generator.chat.assert_not_awaited()
        users.update_conversation_context_summary.assert_not_called()

    def test_compacts_even_when_under_budget_since_manual_is_forced(self):
        # Messages sized so the tail comfortably fits the auto-compaction
        # budget (nothing would fold automatically) while still exceeding
        # force's tighter keep_budget (which reserves room for the summary +
        # the new turn), so forcing genuinely has something to fold.
        long_tail = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": "word " * 100,
             "created_at": i, "rowid": i}
            for i in range(20)
        ]
        users = _users(long_tail)
        generator = _generator(chat_result="a concise summary")
        handler = _handler(users, generator, max_context_tokens=2500, summary_target_tokens=100)

        client = TestClient(_app(handler=handler))
        resp = client.post(f"/conversations/{uuid.uuid4()}/compact")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "compacted"
        generator.chat.assert_awaited_once()
        users.update_conversation_context_summary.assert_called_once()

    def test_compacts_when_over_budget(self):
        big_tail = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": "word " * 100,
             "created_at": i, "rowid": i}
            for i in range(20)
        ]
        users = _users(big_tail)
        generator = _generator(chat_result="a concise summary")
        handler = _handler(users, generator, max_context_tokens=200, summary_target_tokens=20)

        client = TestClient(_app(handler=handler))
        resp = client.post(f"/conversations/{uuid.uuid4()}/compact")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "compacted"
        generator.chat.assert_awaited_once()
        users.update_conversation_context_summary.assert_called_once()
