"""Lean typed config for the standalone 算命 service. Read once from env / .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # LLM reading backend / 解讀後端. "mock" returns a deterministic stub so the whole
    # app runs with no API key (every chart still casts; only the prose is stubbed).
    llm_backend: Literal["anthropic", "mock"] = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    interpretation_max_tokens: int = 900

    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "text"

    # API protection / 快取與限流 (in-process; see fortune/shared/throttle.py)
    cache_enabled: bool = True
    cache_ttl_seconds: int = 600          # deterministic casts & readings are cached per (path, query, body, day)
    cache_max_entries: int = 512
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 240      # per client IP, general endpoints (0 = unlimited)
    llm_rate_limit_per_minute: int = 30   # per client IP, endpoints that may call the LLM
    llm_max_concurrency: int = 4          # server-wide concurrent LLM calls (queue beyond this)

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
