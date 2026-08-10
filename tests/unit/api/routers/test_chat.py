from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.chat import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from tests.unit.conftest import _make_user


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


class TestChatRouter:

    def test_extracts_last_user_message(self):
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="response")

        client = TestClient(_app(handler=handler))
        resp = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "ok"},
                {"role": "user", "content": "last user message"},
            ],
        })
        assert resp.status_code == 200
        call_req = handler.resolve.call_args[0][0]
        assert call_req.last_user_message == "last user message"

    def test_exec_type_is_rag_chat_when_collection_given(self):
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="response")

        client = TestClient(_app(handler=handler))
        resp = client.post("/chat", json={
            "messages": [{"role": "user", "content": "hi"}],
            "collection": "my-col",
        })
        assert resp.status_code == 200
        call_req = handler.resolve.call_args[0][0]
        assert call_req.exec_type == "rag_chat"

    def test_exec_type_is_chat_without_collection(self):
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="response")

        client = TestClient(_app(handler=handler))
        resp = client.post("/chat", json={
            "messages": [{"role": "user", "content": "hi"}],
        })
        assert resp.status_code == 200
        call_req = handler.resolve.call_args[0][0]
        assert call_req.exec_type == "chat"

    def test_history_excludes_current_turn_and_trailing_placeholder(self):
        # Mirrors the real frontend payload shape (actions.ts always appends
        # the current user message plus an empty assistant placeholder
        # before calling this endpoint) -- history must exclude BOTH, not
        # just the trailing placeholder.
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="response")

        messages = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "msg2"},
            {"role": "assistant", "content": ""},
        ]
        client = TestClient(_app(handler=handler))
        client.post("/chat", json={"messages": messages})
        call_req = handler.resolve.call_args[0][0]
        assert call_req.history == [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "reply"},
        ]
        assert call_req.last_user_message == "msg2"

    def test_first_message_of_new_conversation_has_empty_history(self):
        # Regression test: on a brand-new conversation there is no prior
        # conversation_id, so RequestHandler's DB-based history reconstruction
        # never runs -- whatever this route computes is what the model sees
        # unmodified. history must be empty here, not contain the current
        # question (which would send it to the model twice, back-to-back,
        # with no assistant turn between -- breaking chat-template
        # alternation and looking like retrieval/context "isn't working").
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="response")

        messages = [
            {"role": "user", "content": "what does this policy say about backups?"},
            {"role": "assistant", "content": ""},
        ]
        client = TestClient(_app(handler=handler))
        client.post("/chat", json={"messages": messages, "collection": "my-col"})
        call_req = handler.resolve.call_args[0][0]
        assert call_req.history == []
        assert call_req.last_user_message == "what does this policy say about backups?"

    def test_returns_streaming_response_when_stream_true(self):
        async def _stream_gen():
            yield b'{"content":"hello"}\n'
            yield b'{"content":" world"}\n'

        handler = MagicMock()
        handler.resolve = AsyncMock(return_value=_stream_gen())

        client = TestClient(_app(handler=handler))
        resp = client.post("/chat", json={
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        })
        assert resp.status_code == 200
        # resolve was called with stream=True
        _, kwargs = handler.resolve.call_args
        assert kwargs.get("stream") is True or handler.resolve.call_args[0][1] is True
