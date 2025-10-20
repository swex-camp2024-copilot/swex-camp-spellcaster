"""Database configuration and management for the Spellcasters Playground Backend."""

import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .config import settings

logger = logging.getLogger(__name__)


def _ensure_database_directory(database_url: str) -> None:
    """Ensure the directory for a file-based SQLite database exists.

    Handles URLs like "sqlite+aiosqlite:///./data/playground.db". No-op for
    in-memory databases or non-SQLite URLs.
    """

    if "sqlite" not in database_url:
        return

    # Expect pattern ...:///path/to/file.db
    if ":///" not in database_url:
        return
    path_part = database_url.split(":///", 1)[1]

    # Strip query params if present
    path_part = path_part.split("?")[0]

    # Ignore in-memory database
    if path_part.startswith(":memory:"):
        return

    db_path = Path(path_part)
    # Resolve relative paths against project root (repo root), not CWD
    if not db_path.is_absolute():
        repo_root = Path(__file__).resolve().parents[3]
        db_path = (repo_root / db_path).resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)


# Ensure target directory exists before engine initialization
_ensure_database_directory(settings.database_url)

# Create async engine
engine = create_async_engine(settings.database_url, echo=settings.database_echo, future=True)

# Async session factory
async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    """Create all database tables."""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they are registered

            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")
