from __future__ import annotations

import pathlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from hestia.main import create_api


def _settings(**overrides):
    base = dict(
        version="v1", port=5555, services_to_start=["chat"],
        project_root=pathlib.Path("/fake/root"), app_data=pathlib.Path("/fake/data"),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _container(services=None):
    container = MagicMock()
    container.services = services if services is not None else {}
    container.aclose = AsyncMock()
    return container


# ---------------------------------------------------------------------------
# create_api — app construction (no lifespan involved)
# ---------------------------------------------------------------------------

class TestCreateApi:

    def test_sets_title_and_version(self):
        app = create_api()
        assert app.title == "hestIA"
        assert app.version == "alpha_v0.3"

    def test_registers_slowapi_and_correlation_middleware(self):
        app = create_api()
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "SlowAPIMiddleware" in middleware_classes
        assert "CorrelationMiddleware" in middleware_classes

    def test_limiter_attached_to_app_state(self):
        from hestia.api.limiter import limiter
        app = create_api()
        assert app.state.limiter is limiter


# ---------------------------------------------------------------------------
# lifespan — driven via TestClient's context-manager protocol, which runs
# the real ASGI startup/shutdown lifecycle (not just calling the generator
# function directly).
# ---------------------------------------------------------------------------

class TestLifespan:

    def test_startup_wires_container_handler_and_routers(self):
        app = create_api()
        container = _container(services={"chat": MagicMock()})

        with patch("hestia.main.Settings") as mock_settings_cls, \
             patch("hestia.main.setup_logging") as mock_setup_logging, \
             patch("hestia.main.build_container", return_value=container) as mock_build, \
             patch("hestia.main.sync_templates") as mock_sync, \
             patch("hestia.main.RequestHandler") as mock_handler_cls, \
             patch("hestia.main.include_routers") as mock_include, \
             patch("hestia.main.shutdown_logging") as mock_shutdown:
            mock_settings_cls.load.return_value = _settings()

            with TestClient(app):
                mock_setup_logging.assert_called_once()
                mock_build.assert_called_once()
                mock_sync.assert_called_once_with(
                    pathlib.Path("/fake/root") / "hestia" / "templates",
                    pathlib.Path("/fake/data") / "templates",
                )
                mock_handler_cls.assert_called_once()
                mock_include.assert_called_once_with(app, {"chat"})
                assert app.state.container is container
                assert app.state.handler is mock_handler_cls.return_value
                mock_shutdown.assert_not_called()  # not yet — only on exit

            container.aclose.assert_awaited_once()
            mock_shutdown.assert_called_once()

    def test_configures_login_rate_limit_from_auth_service_config(self):
        app = create_api()
        auth_svc = MagicMock()
        auth_svc.config.max_failed_attempts = 7
        auth_svc.config.lockout_duration_minutes = 3
        container = _container(services={"auth": auth_svc})

        with patch("hestia.main.Settings") as mock_settings_cls, \
             patch("hestia.main.setup_logging"), \
             patch("hestia.main.build_container", return_value=container), \
             patch("hestia.main.sync_templates"), \
             patch("hestia.main.RequestHandler"), \
             patch("hestia.main.include_routers"), \
             patch("hestia.main.shutdown_logging"), \
             patch("hestia.main.login_rate_limit") as mock_rate_limit:
            mock_settings_cls.load.return_value = _settings()

            with TestClient(app):
                pass

        mock_rate_limit.configure.assert_called_once_with(7, 3)

    def test_skips_rate_limit_configuration_when_auth_service_absent(self):
        app = create_api()
        container = _container(services={})  # no "auth" key at all

        with patch("hestia.main.Settings") as mock_settings_cls, \
             patch("hestia.main.setup_logging"), \
             patch("hestia.main.build_container", return_value=container), \
             patch("hestia.main.sync_templates"), \
             patch("hestia.main.RequestHandler"), \
             patch("hestia.main.include_routers"), \
             patch("hestia.main.shutdown_logging"), \
             patch("hestia.main.login_rate_limit") as mock_rate_limit:
            mock_settings_cls.load.return_value = _settings()

            with TestClient(app):
                pass

        mock_rate_limit.configure.assert_not_called()

    def test_shutdown_runs_even_when_startup_fails_before_container_is_stored(self):
        # If build_container itself raises, app.state.container was never
        # set -- shutdown must still run cleanly (just skipping aclose())
        # rather than raising an AttributeError on top of the original error.
        app = create_api()

        with patch("hestia.main.Settings") as mock_settings_cls, \
             patch("hestia.main.setup_logging"), \
             patch("hestia.main.build_container", side_effect=RuntimeError("boom")), \
             patch("hestia.main.shutdown_logging") as mock_shutdown:
            mock_settings_cls.load.return_value = _settings()

            with pytest.raises(RuntimeError, match="boom"):
                with TestClient(app):
                    pass

        mock_shutdown.assert_called_once()
