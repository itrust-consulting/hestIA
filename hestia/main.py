from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from hestia.api.error_handlers import register_error_handlers
from hestia.api.limiter import limiter, login_rate_limit
from hestia.api.routers.registry import include_routers
from hestia.config.settings import Settings
from hestia.container import build_container
from hestia.domain.policies.guard import ExecutionPolicy
from hestia.domain.rag.template_sync import sync_templates
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.config import setup_logging, shutdown_logging
from hestia.infrastructure.logging.middleware import CorrelationMiddleware

_log = logging.getLogger("hestia.system")


# @MRS-073, @MRS-092
def create_api() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = Settings.load()
        setup_logging(settings)

        _log.info("startup", extra={"version": settings.version, "port": settings.port,
                                    "services": settings.services_to_start})

        try:
            container = build_container(settings)
            auth_svc = container.services.get("auth")
            if auth_svc and auth_svc.config:
                cfg = auth_svc.config
                login_rate_limit.configure(cfg.max_failed_attempts, cfg.lockout_duration_minutes)
            app.state.container = container
            sync_templates(settings.project_root / "hestia" / "templates", settings.app_data / "templates")
            app.state.handler = RequestHandler(container, policy=ExecutionPolicy())
            include_routers(app, set(container.services.keys()))

            _log.info("startup_complete", extra={"services_started": list(container.services.keys())})
            yield
        finally:
            _log.info("shutdown")
            container = getattr(app.state, "container", None)
            if container is not None:
                await container.aclose()
            shutdown_logging()

    app = FastAPI(lifespan=lifespan, title="hestIA", version="alpha_v0.3")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)
    return app


if __name__ == "__main__":
    settings = Settings.load()
    api = create_api()
    uvicorn.run(api, host="0.0.0.0", port=settings.port, log_level="info")
