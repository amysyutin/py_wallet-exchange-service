from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.internal_exchange_snapshots import router as internal_exchange_snapshots_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version=settings.app_version)
    application.include_router(health_router)
    application.include_router(internal_exchange_snapshots_router)
    return application


app = create_app()
