# Configuration Management for Tele-Google
# Loads and validates environment variables using Pydantic

from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Telegram API Configuration
class TelegramConfig(BaseSettings):
    api_id: int
    api_hash: str = Field(min_length=32)
    phone: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.startswith('+'):
            raise ValueError('Phone number must start with +')
        return v
    
    model_config = SettingsConfigDict(
        env_prefix='TELEGRAM_',
        env_file='.env',
        case_sensitive=False,
        extra='ignore'
    )


# OpenAI API Configuration
class OpenAIConfig(BaseSettings):
    api_key: str = Field(min_length=20)
    model: str = Field(default="gpt-4o-mini")
    max_tokens: int = Field(default=1000)
    temperature: float = Field(default=0.3)
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v.startswith('sk-'):
            raise ValueError('OpenAI API key must start with sk-')
        return v
    
    model_config = SettingsConfigDict(
        env_prefix='OPENAI_',
        env_file='.env',
        case_sensitive=False,
        extra='ignore'
    )


# PostgreSQL Database Configuration
class DatabaseConfig(BaseSettings):
    host: str = Field(default="localhost")
    port: int = Field(default=5433)
    name: str = Field(default="tele_google")
    user: str = Field(default="postgres")
    password: str
    
    model_config = SettingsConfigDict(
        env_prefix='DB_',
        env_file='.env',
        case_sensitive=False,
        extra='ignore'
    )


# Telegram Bot Configuration
class BotConfig(BaseSettings):
    token: str
    admin_user_ids: List[int] = Field(default_factory=list)
    max_results_per_page: int = Field(default=5)
    
    model_config = SettingsConfigDict(
        env_prefix='BOT_',
        env_file='.env',
        case_sensitive=False,
        extra='ignore'
    )


# Application-level Configuration
class AppConfig(BaseSettings):
    channels: str = Field(default="")
    log_level: str = Field(default="INFO")
    session_dir: Path = Field(default=Path("data/sessions"))
    images_dir: Path = Field(default=Path("data/images"))
    
    # Parse comma-separated channels string into a list
    def get_channels_list(self) -> List[str]:
        if not self.channels:
            return []
        return [ch.strip() for ch in self.channels.split(',') if ch.strip()]
    
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=False,
        extra='ignore'
    )


# Main Configuration Class (Singleton)
class Config:
    _instance: Optional['Config'] = None
    
    def __init__(self):
        # Load all configuration sections from .env
        self.telegram = TelegramConfig()  # type: ignore
        self.openai = OpenAIConfig()  # type: ignore
        self.database = DatabaseConfig()  # type: ignore
        self.bot = BotConfig()  # type: ignore
        self.app = AppConfig()  # type: ignore
        
        # Create required directories
        for directory in [self.app.session_dir, self.app.images_dir, Path('logs')]:
            directory.mkdir(parents=True, exist_ok=True)


# Global config instance
_config_instance: Optional[Config] = None


# Get global configuration instance (singleton)
def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
