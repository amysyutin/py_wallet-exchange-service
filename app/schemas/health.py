from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    build_sha: str
    environment: str
    database: Literal["ok"] | None = None
