from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "development", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_name: str = "py-wallet-exchange-service"
    app_version: str = "0.1.0"
    build_sha: str = "unknown"
    environment: Environment = "local"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://wallet:wallet@localhost:5432/wallet"
    exchange_service_host: str = "0.0.0.0"
    exchange_service_port: int = 8002


@lru_cache
def get_settings() -> Settings:
    return Settings()
