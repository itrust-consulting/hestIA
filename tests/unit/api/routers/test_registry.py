from __future__ import annotations

from fastapi import FastAPI

from hestia.api.routers.registry import include_routers


class TestIncludeRouters:

    def test_always_on_routers_included_regardless_of_services(self):
        app = FastAPI()
        include_routers(app, enabled_services=set())
        # health, auth, account, convo, admin are always_on
        route_paths = [r.path for r in app.routes]
        assert any("/health" in p for p in route_paths)

    def test_optional_router_included_when_service_enabled(self):
        app = FastAPI()
        include_routers(app, enabled_services={"encDense"})
        route_paths = [r.path for r in app.routes]
        assert any("/encode" in p for p in route_paths)

    def test_optional_router_excluded_when_service_absent(self):
        app = FastAPI()
        include_routers(app, enabled_services=set())
        route_paths = [r.path for r in app.routes]
        assert not any("/encode" in p for p in route_paths)

    def test_all_services_enables_all_routers(self):
        app = FastAPI()
        include_routers(app, enabled_services={"encDense", "generate", "search", "ingestion"})
        route_paths = [r.path for r in app.routes]
        # check a few service-gated routes exist
        assert any("/encode" in p for p in route_paths)
        assert any("/search" in p for p in route_paths)
