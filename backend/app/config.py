"""Application configuration (§0.1 declared stack).

Secrets are injected via environment / runtime secret mechanisms (deployment.md);
never committed in plaintext (§4 protected). Defaults here are safe for local dev only.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://boards:boards@localhost:5432/boards"

    # CORS: browser origins allowed to call the API (frontend SPA). Comma-separated in env.
    cors_allow_origins: str = "http://localhost:5173"

    # Auth (S-02): HS256, 30 min access token TTL
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    bcrypt_rounds: int = 12

    # Object storage (MinIO / S3)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"
    s3_bucket_attachments: str = "attachments"
    s3_bucket_thumbnails: str = "thumbnails"
    presigned_ttl_seconds: int = 300  # S-06: 5 min

    # Upload limits (S-03)
    max_image_bytes: int = 10 * 1024 * 1024
    max_file_bytes: int = 25 * 1024 * 1024
    max_image_pixels: int = 50_000_000  # decompression-bomb guard
    thumbnail_max_px: int = 400

    # Initial admin seed (Y-02); password injected via env, never committed
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @field_validator("bcrypt_rounds")
    @classmethod
    def _enforce_min_bcrypt_cost(cls, v: int) -> int:
        # security.md S-02: bcrypt cost must be >= 12.
        if v < 12:
            raise ValueError("bcrypt_rounds must be >= 12 (security.md S-02)")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
