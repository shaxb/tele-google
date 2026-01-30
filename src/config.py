"""
Configuration Management for Tele-Google
Loads and validates environment variables using Pydantic

Main Components:
    - TelegramConfig: Telegram API credentials
    - OpenAIConfig: OpenAI API settings
    - MeilisearchConfig: Search engine configuration
    - DatabaseConfig: PostgreSQL connection settings
    - BotConfig: Telegram bot settings
    - AppConfig: Application-level settings
    - Config: Main configuration class (singleton)

Usage:
    from src.config import get_config
    config = get_config()
    print(config.telegram.api_id)
"""
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    """
    Telegram API Configuration
    
    Get credentials from: https://my.telegram.org/apps
    
    Attributes:
        api_id: Telegram API ID
        api_hash: Telegram API Hash (32+ characters)
        phone: Phone number with country code (e.g., +998901234567)
    """
    api_id: int = Field(..., description="Telegram API ID from my.telegram.org")
    api_hash: str = Field(..., min_length=32, description="Telegram API Hash")
    phone: str = Field(..., description="Phone number with country code (+998...)")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format"""
        if not v.startswith('+'):
            raise ValueError('Phone number must start with +')
        if not v[1:].replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits after +')
        return v
    
    model_config = SettingsConfigDict(
        env_prefix='TELEGRAM_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class OpenAIConfig(BaseSettings):
    """
    OpenAI API Configuration
    
    Get API key from: https://platform.openai.com/api-keys
    
    Attributes:
        api_key: OpenAI API key (starts with sk-)
        model: Model to use (default: gpt-4o-mini)
        max_tokens: Maximum tokens per request
        temperature: Randomness in responses (0.0-1.0, lower = more deterministic)
    """
    api_key: str = Field(..., min_length=20, description="OpenAI API key")
    model: str = Field(default="gpt-4o-mini", description="Model to use for AI processing")
    max_tokens: int = Field(default=1000, description="Maximum tokens per request")
    temperature: float = Field(default=0.3, description="Temperature for AI responses")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate OpenAI API key format"""
        if not v.startswith('sk-'):
            raise ValueError('OpenAI API key must start with sk-')
        return v
    
    model_config = SettingsConfigDict(
        env_prefix='OPENAI_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class MeilisearchConfig(BaseSettings):
    """
    Meilisearch Configuration
    
    Meilisearch runs in Docker container (see docker-compose.yml)
    
    Attributes:
        host: Meilisearch URL (default: http://localhost:7700)
        master_key: Master key for authentication
        index: Index name for marketplace documents
    """
    host: str = Field(default="http://localhost:7700", description="Meilisearch host URL")
    master_key: str = Field(..., description="Meilisearch master key")
    index: str = Field(default="marketplace", description="Index name for documents")
    
    @field_validator('host')
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate Meilisearch host URL"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Meilisearch host must start with http:// or https://')
        return v.rstrip('/')
    
    model_config = SettingsConfigDict(
        env_prefix='MEILI_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class DatabaseConfig(BaseSettings):
    """
    PostgreSQL Database Configuration
    
    PostgreSQL runs in Docker container (see docker-compose.yml)
    Note: Using port 5433 to avoid conflicts with other PostgreSQL instances
    
    Attributes:
        host: Database host
        port: Database port
        name: Database name
        user: Database user
        password: Database password
    """
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5433, description="Database port")
    name: str = Field(default="tele_google", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(..., description="Database password")
    
    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string for psycopg2"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_connection_string(self) -> str:
        """Generate async PostgreSQL connection string for asyncpg/SQLAlchemy"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    model_config = SettingsConfigDict(
        env_prefix='DB_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class BotConfig(BaseSettings):
    """
    Telegram Bot Configuration
    
    Get bot token from @BotFather on Telegram
    
    Attributes:
        token: Bot token from @BotFather
        admin_user_ids: List of admin Telegram user IDs (optional)
        max_results_per_page: Maximum search results per page
    """
    token: str = Field(..., description="Bot token from @BotFather")
    admin_user_ids: List[int] = Field(default_factory=list, description="Admin user IDs")
    max_results_per_page: int = Field(default=10, description="Maximum results per search page")
    
    @field_validator('token')
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate bot token format"""
        parts = v.split(':')
        if len(parts) != 2 or not parts[0].isdigit():
            raise ValueError('Invalid bot token format')
        return v
    
    model_config = SettingsConfigDict(
        env_prefix='BOT_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class AppConfig(BaseSettings):
    """
    Application-level Configuration
    
    Attributes:
        channels: Comma-separated list of channels to monitor (e.g., "@Channel1,@Channel2")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        session_dir: Directory for Telegram session files
        images_dir: Directory for downloaded images
    """
    channels: str = Field(
        default="", 
        description="Comma-separated list of channels to monitor"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    session_dir: Path = Field(default=Path("data/sessions"), description="Directory for session files")
    images_dir: Path = Field(default=Path("data/images"), description="Directory for downloaded images")
    
    def get_channels_list(self) -> List[str]:
        """
        Parse comma-separated channels string into a list
        
        Returns:
            List of channel usernames (e.g., ["@Channel1", "@Channel2"])
        """
        if not self.channels:
            return []
        return [ch.strip() for ch in self.channels.split(',') if ch.strip()]
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class Config:
    """
    Main Configuration Class (Singleton Pattern)
    
    Combines all configuration sections and provides global access.
    Use get_config() function to access the singleton instance.
    
    Attributes:
        telegram: Telegram API configuration
        openai: OpenAI API configuration
        meilisearch: Meilisearch configuration
        database: PostgreSQL configuration
        bot: Telegram bot configuration
        app: Application-level configuration
    
    Example:
        from src.config import get_config
        config = get_config()
        print(config.telegram.api_id)
    """
    _instance: Optional['Config'] = None
    
    def __init__(self):
        """Initialize configuration from environment variables (.env file)"""
        # Check if .env file exists
        env_file = Path('.env')
        if not env_file.exists():
            print(f"Warning: .env file not found at {env_file.absolute()}")
            print(f"Copy .env.template to .env and configure your settings")
        
        # Initialize all configuration sections
        # Pydantic automatically loads from .env file
        self.telegram = TelegramConfig()  # type: ignore
        self.openai = OpenAIConfig()  # type: ignore
        self.meilisearch = MeilisearchConfig()  # type: ignore
        self.database = DatabaseConfig()  # type: ignore
        self.bot = BotConfig()  # type: ignore
        self.app = AppConfig()  # type: ignore
        
        # Create required data directories
        self._create_directories()
    
    def _create_directories(self):
        """Create required data directories if they don't exist"""
        directories = [
            self.app.session_dir,
            self.app.images_dir,
            Path('data/meili_data'),
            Path('logs')
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_instance(cls) -> 'Config':
        """Get singleton instance of Config"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def validate(self) -> bool:
        """
        Validate all configuration settings
        
        Returns:
            True if all validations pass
            
        Raises:
            RuntimeError: If any validation fails
        """
        try:
            # All Pydantic validations happen automatically in __init__
            # This method performs additional runtime checks
            
            # Validate channels list is not empty
            channels_list = self.app.get_channels_list()
            if not channels_list:
                raise ValueError("CHANNELS must contain at least one channel (e.g., @Channel1,@Channel2)")
            
            # Validate channel format (must start with @)
            for channel in channels_list:
                if not channel.startswith('@'):
                    raise ValueError(f"Channel '{channel}' must start with @ symbol")
            
            return True
            
        except Exception as e:
            raise RuntimeError(f"Configuration validation failed: {e}")
    
    def get_monitored_channels(self) -> List[str]:
        """
        Get list of channels to monitor
        
        Returns:
            List of channel usernames
        """
        return self.app.get_channels_list()
    
    def print_summary(self):
        """Print configuration summary (without sensitive data)"""
        print("=" * 60)
        print("CONFIGURATION SUMMARY")
        print("=" * 60)
        print(f"Telegram API ID:      {self.telegram.api_id}")
        print(f"Telegram Phone:       {self.telegram.phone}")
        print(f"OpenAI Model:         {self.openai.model}")
        print(f"Meilisearch Host:     {self.meilisearch.host}")
        print(f"Meilisearch Index:    {self.meilisearch.index}")
        print(f"Database Host:        {self.database.host}:{self.database.port}")
        print(f"Database Name:        {self.database.name}")
        print(f"Bot Token:            {self.bot.token[:10]}***")
        print(f"Monitored Channels:   {', '.join(self.get_monitored_channels())}")
        print(f"Log Level:            {self.app.log_level}")
        print(f"Session Directory:    {self.app.session_dir}")
        print(f"Images Directory:     {self.app.images_dir}")
        print("=" * 60)


# ============================================================================
# GLOBAL ACCESS TO CONFIGURATION
# ============================================================================

# Global config instance - lazy initialization
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance (singleton pattern)
    
    Returns:
        Config: Global configuration instance
        
    Example:
        config = get_config()
        print(config.telegram.api_id)
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config.get_instance()
    return _config_instance


def validate_environment() -> bool:
    """
    Validate environment configuration at startup
    
    Returns:
        True if validation passes, False otherwise
        
    Usage:
        Call this at application startup to ensure proper configuration
    """
    try:
        config = get_config()
        config.validate()
        return True
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
        print("\nPlease check your .env file and ensure all required variables are set.")
        print("You can copy .env.template to .env and fill in the values.")
        return False


# ============================================================================
# TEST CONFIGURATION (Run this file directly to test)
# ============================================================================


if __name__ == '__main__':
    """Test configuration loading"""
    try:
        config = Config.get_instance()
        config.print_summary()
        
        if config.validate():
            print("\n✓ All configuration settings are valid!")
        else:
            print("\n✗ Configuration validation failed!")
            
    except Exception as e:
        print(f"\n✗ Configuration error: {e}")
        print("\nMake sure you have a .env file with all required settings.")
        print("Copy .env.template to .env and fill in your values.")
