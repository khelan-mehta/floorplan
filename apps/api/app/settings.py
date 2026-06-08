from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_schemas_dir() -> str:
    # repo-root/packages/schemas/schemas relative to this file (apps/api/app/settings.py)
    return str(Path(__file__).resolve().parents[3] / "packages" / "schemas" / "schemas")


class Settings(BaseSettings):
    """Typed application configuration. No hard-coded config elsewhere."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    service_name: str = "api"
    log_level: str = "info"

    # Persistence (MongoDB)
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "fpg"
    redis_url: str = "redis://localhost:6379/0"

    # Object storage (artifacts)
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "fpg-artifacts"
    s3_access_key: str = "fpg"
    s3_secret_key: str = "fpg_dev_password"

    # Auth
    jwt_secret: str = "change_me_in_prod"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_minutes: int = 60 * 24 * 14

    # CORS — the web app origin(s)
    cors_origins: list[str] = ["http://localhost:5173"]

    # Canonical JSON Schemas (Phase 02) for domain-document validation on write.
    schemas_dir: str = ""

    # Downstream service URLs
    generator_url: str = "http://localhost:8001"
    codes_url: str = "http://localhost:8002"
    validator_url: str = "http://localhost:8003"
    geometry_url: str = "http://localhost:8004"
    export_url: str = "http://localhost:8005"

    def resolved_schemas_dir(self) -> str:
        return self.schemas_dir or _default_schemas_dir()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
