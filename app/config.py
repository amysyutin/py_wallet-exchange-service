from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "development", "test", "staging", "production"]
SECURE_ENVIRONMENTS = frozenset({"staging", "production"})
INSECURE_INTERNAL_API_TOKENS = frozenset(
    {"change-me", "changeme", "password", "secret", "test-token"}
)
MIN_PRODUCTION_TOKEN_LENGTH = 32


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
    internal_api_token: str = ""
    exchange_service_host: str = "0.0.0.0"
    exchange_service_port: int = 8002

    binance_base_url: str = "https://api.binance.com"
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_timeout_seconds: float = Field(default=10, gt=0, le=60)
    binance_recv_window_ms: int = Field(default=5000, ge=1, le=60000)

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_internal_api_token(self) -> Self:
        token = self.internal_api_token
        if not token or not token.strip():
            raise ValueError("INTERNAL_API_TOKEN is required")
        if token != token.strip():
            raise ValueError("INTERNAL_API_TOKEN must not contain surrounding whitespace")
        if self.environment in SECURE_ENVIRONMENTS:
            if token.lower() in INSECURE_INTERNAL_API_TOKENS:
                raise ValueError("INTERNAL_API_TOKEN cannot use a known placeholder")
            if len(token) < MIN_PRODUCTION_TOKEN_LENGTH:
                raise ValueError(
                    "INTERNAL_API_TOKEN must be at least "
                    f"{MIN_PRODUCTION_TOKEN_LENGTH} characters in staging or production"
                )
            if not self.binance_base_url.startswith("https://"):
                raise ValueError("BINANCE_BASE_URL must use HTTPS in staging or production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
