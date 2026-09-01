from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./agentcloud.db"
    redis_url: str = "redis://localhost:6379/0"
    api_keys: Annotated[dict[str, str], NoDecode] = Field(
        default_factory=lambda: {"dev-client": "change-me"}
    )
    llm_provider: str = "mock"
    llm_model: str = "mock-v1"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    worker_max_retries: int = 3
    worker_retry_base_seconds: float = 1.0
    otel_exporter_otlp_endpoint: str | None = None
    log_level: str = "INFO"

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        pairs: dict[str, str] = {}
        for item in value.split(","):
            client, separator, secret = item.partition(":")
            if separator and client.strip() and secret.strip():
                pairs[client.strip()] = secret.strip()
        if not pairs:
            raise ValueError("API_KEYS must contain client:secret pairs")
        return pairs


@lru_cache
def get_settings() -> Settings:
    return Settings()
