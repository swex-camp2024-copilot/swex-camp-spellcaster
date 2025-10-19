"""Configuration settings for the Spellcasters Playground Backend."""

from pathlib import Path

from pydantic_settings import BaseSettings


def _default_database_url() -> str:
    """Compute an absolute SQLite URL pointing to <repo_root>/data/playground.db.

    Ensures the path is independent of the current working directory.
    """
    repo_root = Path(__file__).resolve().parents[3]
    db_path = (repo_root / "data" / "playground.db").resolve()
    # Four slashes after scheme for absolute paths, e.g., sqlite+aiosqlite:////abs/path
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Database
    database_url: str = _default_database_url()
    database_echo: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Game settings
    turn_timeout_seconds: float = 5.0
    match_loop_delay_seconds: float = 1.0
    max_turns_per_match: int = 100

    # Session management
    session_cleanup_minutes: int = 30
    max_concurrent_sessions: int = 50

    # Logging
    log_level: str = "INFO"
    log_dir: str = "backend/logs"
    playground_log_dir: str = "backend/logs/playground"

    # Security
    cors_origins: list[str] = ["*"]

    # Bot execution
    bot_execution_timeout: float = 1.0
    max_bot_memory_mb: int = 100

    # Visualization
    enable_visualization: bool = True
    max_visualized_sessions: int = 10
    visualizer_queue_size: int = 100
    visualizer_shutdown_timeout: float = 5.0
    visualizer_animation_duration: float = 0.5
    visualizer_initial_render_delay: float = 0.3

    model_config = {"env_file": ".env", "env_prefix": "PLAYGROUND_", "case_sensitive": False}


# Global settings instance
settings = Settings()
