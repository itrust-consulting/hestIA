
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from hestia.settings import Settings
from hestia.container import build_container, AppStartupConfig
from hestia.routes.registry import include_routers
from hestia.frontend.gui.app import create_gui


def create_api() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):

        s = Settings()  
        cfg = AppStartupConfig(
            llm_backend=s.LLM_BACKEND,
            db_backend=s.DB_BACKEND,
            services_to_start=s.SERVICES_TO_START,
        )

        container = build_container(s, cfg)
        app.state.container = container
        
        enabled_services = set(container.services.keys())
        include_routers(app, enabled_services)
        yield

    return FastAPI(lifespan=lifespan, title="hestIA")


if __name__=="__main__":

    api = create_api()
    gui = create_gui(api)
    uvicorn.run(gui, host="0.0.0.0", port=7860, log_level="debug")
