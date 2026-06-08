"""Typed configuration for the codes service. No hard-coded config elsewhere."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "codes"

    # Rule extraction via the OpenAI API (optional; deterministic fallback used when empty).
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""  # optional override (Azure/proxy/compatible endpoints)

    # Vector store. Empty => in-memory hybrid index (dev default). Qdrant is the production target.
    qdrant_url: str = ""
    embedding_dim: int = 256
    retrieval_alpha: float = 0.5  # dense vs keyword blend


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
