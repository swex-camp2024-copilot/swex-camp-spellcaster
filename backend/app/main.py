"""Spellcasters Playground Backend - FastAPI Application."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.database import create_tables
from .core.error_handlers import register_error_handlers
from .core.state import get_state_manager, initialize_state_manager, shutdown_state_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Spellcasters Playground Backend...")

    # Create database tables
    await create_tables()
    logger.info("Database tables created/verified")

    # Initialize state manager with all services
    await initialize_state_manager()
    logger.info("State manager initialized")

    # Register error handlers
    register_error_handlers(app)
    logger.info("Error handlers registered")

    logger.info("Spellcasters Playground Backend started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Spellcasters Playground Backend...")

    # Shutdown state manager and all services
    await shutdown_state_manager()
    logger.info("State manager shutdown complete")

    logger.info("Spellcasters Playground Backend shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Spellcasters Playground Backend",
    description="Backend API for the Spellcasters Hackathon Playground mode",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint with service status details.

    Returns:
        Health status including all service states
    """
    try:
        state_manager = get_state_manager()
        health = state_manager.get_health()

        return {
            "status": "healthy" if state_manager.is_ready else "degraded",
            "service": "spellcasters-playground-backend",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "state_manager": health,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "spellcasters-playground-backend",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


# Statistics endpoint
@app.get("/stats")
async def get_statistics() -> Dict[str, Any]:
    """Get system statistics.

    Returns:
        System statistics including active sessions, connections, etc.
    """
    try:
        state_manager = get_state_manager()
        stats = state_manager.get_statistics()

        return {
            "service": "spellcasters-playground-backend",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return {
            "service": "spellcasters-playground-backend",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


# Root endpoint
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {"message": "Spellcasters Playground Backend API", "version": "1.0.0", "docs": "/docs"}


# Include API routers
from .api import players, sessions, streaming, actions, replay, admin

app.include_router(players.router, tags=["players"])
app.include_router(sessions.router, tags=["sessions"])
app.include_router(streaming.router, tags=["streaming"])
app.include_router(actions.router, tags=["actions"])
app.include_router(replay.router, tags=["replay"])
app.include_router(admin.router, tags=["admin"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
