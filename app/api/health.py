from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _health_response(*, database: Literal["ok"] | None = None) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        build_sha=settings.build_sha,
        environment=settings.environment,
        database=database,
    )


def _readiness(database: Session) -> HealthResponse:
    try:
        database.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from error
    return _health_response(database="ok")


@router.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return _health_response()


@router.get("/health/ready", response_model=HealthResponse)
def readiness(database: DatabaseSession) -> HealthResponse:
    return _readiness(database)


@router.get("/health", response_model=HealthResponse)
def health(database: DatabaseSession) -> HealthResponse:
    return _readiness(database)
