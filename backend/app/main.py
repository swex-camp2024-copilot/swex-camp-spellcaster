"""Spellcasters Playground Backend - FastAPI Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any

from .core.config import settings
from .core.database import create_tables
from .core.exceptions import PlaygroundError
from .models.errors import ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Spellcasters Playground Backend...")
    await create_tables()
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Spellcasters Playground Backend...")


# Create FastAPI application
app = FastAPI(
    title="Spellcasters Playground Backend",
    description="Backend API for the Spellcasters Hackathon Playground mode",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for PlaygroundError
@app.exception_handler(PlaygroundError)
async def playground_error_handler(request, exc: PlaygroundError) -> JSONResponse:
    """Handle custom playground errors."""
    logger.error(f"Playground error: {exc}", extra={"error_type": type(exc).__name__})
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=type(exc).__name__.replace("Error", "").upper(),
            message=str(exc),
            session_id=getattr(exc, "session_id", None)
        ).model_dump()
    )


# Global exception handler for general exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred"
        ).model_dump()
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "spellcasters-playground-backend",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Spellcasters Playground Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# TODO: Include API routers here when they are implemented
# app.include_router(players.router, prefix="/players", tags=["players"])
# app.include_router(sessions.router, prefix="/playground", tags=["sessions"])
# app.include_router(streaming.router, prefix="/playground", tags=["streaming"])
# app.include_router(actions.router, prefix="/playground", tags=["actions"])
# app.include_router(replay.router, prefix="/playground", tags=["replay"])
# app.include_router(admin.router, prefix="/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 