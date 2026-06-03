from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request


class TestGetContainer:

    def _request(self, container=None):
        app = MagicMock()
        app.state.container = container
        req = MagicMock(spec=Request)
        req.app = app
        return req

    def test_returns_container_when_present(self):
        from hestia.api.dependencies import get_container
        container = MagicMock()
        req = self._request(container=container)
        result = get_container(req)
        assert result is container

    def test_raises_503_when_missing(self):
        from hestia.api.dependencies import get_container
        app = MagicMock()
        del app.state.container
        app.state = MagicMock(spec=[])
        req = MagicMock(spec=Request)
        req.app = app
        with pytest.raises(HTTPException) as exc_info:
            get_container(req)
        assert exc_info.value.status_code == 503


class TestGetHandler:

    def _request(self, handler=None):
        app = MagicMock()
        app.state.handler = handler
        req = MagicMock(spec=Request)
        req.app = app
        return req

    def test_returns_handler_when_present(self):
        from hestia.api.dependencies import get_handler
        handler = MagicMock()
        req = self._request(handler=handler)
        result = get_handler(req)
        assert result is handler

    def test_raises_503_when_missing(self):
        from hestia.api.dependencies import get_handler
        app = MagicMock()
        app.state = MagicMock(spec=[])
        req = MagicMock(spec=Request)
        req.app = app
        with pytest.raises(HTTPException) as exc_info:
            get_handler(req)
        assert exc_info.value.status_code == 503
