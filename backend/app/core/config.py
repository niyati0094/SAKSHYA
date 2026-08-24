"""Application configuration.

All settings are environment-driven with the ``SAKSHYA_`` prefix.
No secret is ever hard-coded for non-development environments: if the app is
started outside development without an explicit secret key, it refuses to boot.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Clearly-labelled development-only signing key. This exists so the prototype
# can be cloned and run with zero setup. It is NOT a secret and must never be
# used outside local development - see `Settings.validate_runtime`.
DEV_ONLY_SECRET_KEY = "dev-only-insecure-key-do-not-use-outside-local-development"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SAKSHYA_",
        extra="ignore",
    )

    app_name: str = "SAKSHYA"
    app_description: str = (
        "Evidence-based competency intelligence for India's Official Statistical System"
    )
    environment: str = "development"

    # Auth
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # one working day

    # Database. SQLite for the local prototype; swap to a PostgreSQL URL to use
    # the pgvector-backed adapter (see docs/ARCHITECTURE.md).
    database_url: str = "sqlite:///./sakshya.db"

    # CORS - comma-separated origins
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local", "test"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_secret_key(self) -> str:
        """Resolve the signing key, falling back to the dev key in development only."""
        if self.secret_key:
            return self.secret_key
        return DEV_ONLY_SECRET_KEY

    def validate_runtime(self) -> None:
        """Fail fast rather than silently signing tokens with a public key."""
        if not self.is_development and not self.secret_key:
            raise RuntimeError(
                "SAKSHYA_SECRET_KEY must be set when SAKSHYA_ENVIRONMENT is not "
                "'development'. Refusing to start with the development key."
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
