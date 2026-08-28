"""
Settings for vera-api.

Loaded via pydantic-settings from environment variables (or a .env file at the
repo root). All secrets are excluded from repr/logging automatically because
they use SecretStr.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: SecretStr = SecretStr("")
    # Service-role key is used server-side only (never sent to clients).
    supabase_service_role_key: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("postgresql+asyncpg://postgres:postgres@localhost:54322/postgres")

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False


# Singleton — import this everywhere instead of constructing a new Settings().
settings = Settings()
