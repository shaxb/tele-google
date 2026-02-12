"""Configuration management — loads and validates .env using Pydantic."""

from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    api_id: int
    api_hash: str = Field(min_length=32)
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith("+"):
            raise ValueError("Phone number must start with +")
        return v

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_", env_file=".env", extra="ignore")


class OpenAIConfig(BaseSettings):
    api_key: str = Field(min_length=20)
    model: str = "gpt-4o-mini"

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with sk-")
        return v

    model_config = SettingsConfigDict(env_prefix="OPENAI_", env_file=".env", extra="ignore")


class DatabaseConfig(BaseSettings):
    host: str = "localhost"
    port: int = 5433
    name: str = "tele_google"
    user: str = "postgres"
    password: str

    model_config = SettingsConfigDict(env_prefix="DB_", env_file=".env", extra="ignore")


class BotConfig(BaseSettings):
    token: str
    admin_user_ids: List[int] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_prefix="BOT_", env_file=".env", extra="ignore")


class Config:
    """Aggregates all config sections. Use ``get_config()`` to access."""

    def __init__(self) -> None:
        self.telegram = TelegramConfig()  # type: ignore[call-arg]
        self.openai = OpenAIConfig()  # type: ignore[call-arg]
        self.database = DatabaseConfig()  # type: ignore[call-arg]
        self.bot = BotConfig()  # type: ignore[call-arg]

        # Ensure runtime directories exist
        for d in [Path("data/sessions"), Path("data/images"), Path("logs")]:
            d.mkdir(parents=True, exist_ok=True)


_config: Optional[Config] = None


def get_config() -> Config:
    """Lazy singleton for the global config."""
    global _config
    if _config is None:
        _config = Config()
    return _config
