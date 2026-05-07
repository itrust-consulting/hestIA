
from contextlib import asynccontextmanager
from fastapi import FastAPI

import uvicorn

import hestia.settings as s
from hestia.container import build_container, AppStartupConfig
from hestia.routes.registry import include_routers

from hestia.handler import RequestHandler
from hestia.utils.policies import ExecutionPolicy


def create_api() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):

        cfg = AppStartupConfig(
            llm_backend=s.LLM_BACKEND,
            db_backend=s.DB_BACKEND,
            services_to_start=s.SERVICES_TO_START,
            enable_auth=s.ENABLE_AUTH,
        )

        container = build_container(s, cfg)
        app.state.container = container
        app.state.handler = RequestHandler(container, policy=ExecutionPolicy())
        
        enabled_services = set(container.services.keys())
        include_routers(app, enabled_services)
        yield

    return FastAPI(lifespan=lifespan, title="hestIA")


if __name__=="__main__":

    api = create_api()
    uvicorn.run(api, host="0.0.0.0", port=s.PORT, log_level="debug")
