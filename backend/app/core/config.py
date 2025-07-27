"""Configuration settings for the Spellcasters Playground Backend."""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./playground.db"
    database_echo: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # Game settings
    turn_timeout_seconds: float = 5.0
    match_loop_delay_seconds: float = 1.0
    max_turns_per_match: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_dir: str = "backend/logs"
    playground_log_dir: str = "backend/logs/playground"
    
    # Security
    cors_origins: list[str] = ["*"]
    
    # Bot execution
    bot_execution_timeout: float = 1.0
    max_bot_memory_mb: int = 100
    
    model_config = {
        "env_file": ".env",
        "env_prefix": "PLAYGROUND_",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings() 