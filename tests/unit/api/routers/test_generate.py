from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.generate import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from tests.unit.conftest import _make_user


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


class TestGenerateRouter:

    def test_non_streaming_returns_resolved_response(self):
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="generated text")

        client = TestClient(_app(handler=handler))
        resp = client.post("/generate", json={"prompt": "hello"})

        assert resp.status_code == 200
        assert resp.text == "generated text"
        call_req = handler.resolve.call_args[0][0]
        assert call_req.prompt == "hello"

    def test_exec_type_is_rag_generate_when_collection_given(self):
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="text")

        client = TestClient(_app(handler=handler))
        client.post("/generate", json={"prompt": "hi", "collection": "my-col"})

        call_req = handler.resolve.call_args[0][0]
        assert call_req.exec_type == "rag_generate"
        assert call_req.collection == "my-col"

    def test_exec_type_is_generate_without_collection(self):
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="text")

        client = TestClient(_app(handler=handler))
        client.post("/generate", json={"prompt": "hi"})

        assert handler.resolve.call_args[0][0].exec_type == "generate"

    def test_forwards_model_and_kwargs(self):
        handler = MagicMock()
        handler.resolve = AsyncMock(return_value="text")

        client = TestClient(_app(handler=handler))
        client.post("/generate", json={
            "prompt": "hi", "model": "m1", "model_kwargs": {"temperature": 0.2}, "query_kwargs": {"limit": 5},
        })

        call_req = handler.resolve.call_args[0][0]
        assert call_req.model == "m1"
        assert call_req.model_kwargs == {"temperature": 0.2}
        assert call_req.query_kwargs == {"limit": 5}

    def test_returns_streaming_response_when_stream_true(self):
        async def _stream_gen():
            yield b'{"content":"hello"}\n'

        handler = MagicMock()
        handler.resolve = AsyncMock(return_value=_stream_gen())

        client = TestClient(_app(handler=handler))
        resp = client.post("/generate", json={"prompt": "hi", "stream": True})

        assert resp.status_code == 200
        assert handler.resolve.call_args.kwargs.get("stream") is True
