"""
Application settings loaded from environment variables.
Uses Pydantic Settings for validation and type safety.
"""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application configuration is loaded from environment variables.
    See .env.example for documentation of each variable.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Telegram ---
    bot_token: str

    # --- Database ---
    database_url: str

    # --- Application ---
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Admin bootstrap ---
    # Comma-separated Telegram user IDs, e.g. "123,456"
    admin_telegram_ids: str = ""

    # --- Security ---
    max_photo_size_mb: int = 10
    rate_limit_per_minute: int = 20

    # --- Student privacy ---
    student_lookup_mode: Literal["linked", "open"] = "linked"

    # ------------------------------------------------------------------ #
    # Derived / validated fields                                           #
    # ------------------------------------------------------------------ #

    @field_validator("bot_token")
    @classmethod
    def bot_token_must_not_be_placeholder(cls, v: str) -> str:
        if not v or v == "your_telegram_bot_token_here":
            raise ValueError(
                "BOT_TOKEN is not configured. "
                "Set it in your .env file."
            )
        return v

    @field_validator("database_url")
    @classmethod
    def database_url_must_use_asyncpg(cls, v: str) -> str:
        """Ensure the async driver is used."""
        if "postgresql://" in v and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    @model_validator(mode="after")
    def validate_admin_ids(self) -> "Settings":
        """Parse and validate the admin IDs string."""
        if self.admin_telegram_ids:
            raw = self.admin_telegram_ids
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            for part in parts:
                if not part.isdigit():
                    raise ValueError(
                        f"ADMIN_TELEGRAM_IDS contains non-numeric value: '{part}'. "
                        "All IDs must be integers."
                    )
        return self

    def get_admin_telegram_ids(self) -> list[int]:
        """Return admin Telegram user IDs as a list of integers."""
        if not self.admin_telegram_ids:
            return []
        return [
            int(p.strip())
            for p in self.admin_telegram_ids.split(",")
            if p.strip().isdigit()
        ]

    @property
    def max_photo_size_bytes(self) -> int:
        """Maximum allowed photo size in bytes."""
        return self.max_photo_size_mb * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.
    Use this everywhere instead of constructing Settings() directly.
    """
    return Settings()  # type: ignore[call-arg]
