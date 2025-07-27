"""Database configuration and management for the Spellcasters Playground Backend."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .config import settings

logger = logging.getLogger(__name__)

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
