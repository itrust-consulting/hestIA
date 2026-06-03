"""Shared fixtures for router tests using FastAPI TestClient."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.security import get_current_user
from hestia.api.dependencies import get_container, get_handler
from tests.unit.conftest import _make_user


def _build_app(router, *, user=None, container=None, handler=None):
    """Minimal FastAPI app with one router and dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    resolved_user = user or _make_user(is_admin=True)
    resolved_container = container or MagicMock()
    resolved_handler = handler or MagicMock()

    app.dependency_overrides[get_current_user] = lambda: resolved_user
    app.dependency_overrides[get_container] = lambda: resolved_container
    app.dependency_overrides[get_handler] = lambda: resolved_handler

    return app, resolved_container, resolved_handler


@pytest.fixture
def admin_client():
    """Return a helper that builds a TestClient for a router with an admin user."""
    def factory(router, container=None, handler=None):
        app, c, h = _build_app(router, user=_make_user(is_admin=True),
                                container=container, handler=handler)
        return TestClient(app), c, h
    return factory
