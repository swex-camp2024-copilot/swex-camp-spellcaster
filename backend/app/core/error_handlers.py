"""Global exception handlers for the Spellcasters Playground Backend.

This module provides centralized error handling for all custom exceptions,
ensuring consistent error responses and security-aware logging.
"""

import logging
from typing import Any, Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from .exceptions import (
    AuthorizationError,
    BotExecutionError,
    BotTimeoutError,
    ConfigurationError,
    DatabaseError,
    GameEngineError,
    InvalidActionError,
    InvalidTurnError,
    PlaygroundError,
    PlayerNotFoundError,
    PlayerRegistrationError,
    RateLimitError,
    SessionAlreadyActiveError,
    SessionNotFoundError,
    SSEConnectionError,
    ValidationError,
)
from ..models.errors import (
    ErrorResponse,
    GameEngineErrorResponse,
    RateLimitErrorResponse,
    TimeoutErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)

logger = logging.getLogger(__name__)


def _sanitize_error_for_logging(exc: Exception) -> Dict[str, Any]:
    """Sanitize exception data for secure logging.

    Removes potentially sensitive information while preserving debugging context.

    Args:
        exc: The exception to sanitize

    Returns:
        Dictionary with safe logging data
    """
    safe_data = {
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }

    # Add safe attributes from custom exceptions
    if isinstance(exc, PlaygroundError):
        if hasattr(exc, "session_id") and exc.session_id:
            safe_data["session_id"] = exc.session_id
        if hasattr(exc, "status_code"):
            safe_data["status_code"] = exc.status_code

    return safe_data


# Base PlaygroundError handler
async def playground_error_handler(request: Request, exc: PlaygroundError) -> JSONResponse:
    """Handle base playground errors.

    Args:
        request: The FastAPI request object
        exc: The PlaygroundError exception

    Returns:
        JSON response with error details
    """
    logger.error(f"Playground error: {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=type(exc).__name__.replace("Error", "").upper(),
            message=exc.message,
            details=exc.details if exc.details else None,
            session_id=exc.session_id,
        ).model_dump(mode="json"),
    )


# Player-related error handlers
async def player_not_found_error_handler(request: Request, exc: PlayerNotFoundError) -> JSONResponse:
    """Handle player not found errors.

    Args:
        request: The FastAPI request object
        exc: The PlayerNotFoundError exception

    Returns:
        JSON response with error details
    """
    logger.warning(f"Player not found: {exc.player_id}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="PLAYER_NOT_FOUND",
            message=str(exc),
            details={"player_id": exc.player_id},
        ).model_dump(mode="json"),
    )


async def player_registration_error_handler(request: Request, exc: PlayerRegistrationError) -> JSONResponse:
    """Handle player registration errors.

    Args:
        request: The FastAPI request object
        exc: The PlayerRegistrationError exception

    Returns:
        JSON response with error details
    """
    logger.warning(f"Player registration failed: {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="PLAYER_REGISTRATION_ERROR",
            message=str(exc),
        ).model_dump(mode="json"),
    )


# Session-related error handlers
async def session_not_found_error_handler(request: Request, exc: SessionNotFoundError) -> JSONResponse:
    """Handle session not found errors.

    Args:
        request: The FastAPI request object
        exc: The SessionNotFoundError exception

    Returns:
        JSON response with error details
    """
    logger.warning(f"Session not found: {exc.session_id}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="SESSION_NOT_FOUND",
            message=str(exc),
            session_id=exc.session_id,
        ).model_dump(mode="json"),
    )


async def session_already_active_error_handler(request: Request, exc: SessionAlreadyActiveError) -> JSONResponse:
    """Handle session already active errors.

    Args:
        request: The FastAPI request object
        exc: The SessionAlreadyActiveError exception

    Returns:
        JSON response with error details
    """
    logger.warning(f"Session already active: {exc.session_id}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            error="SESSION_ALREADY_ACTIVE",
            message=str(exc),
            session_id=exc.session_id,
        ).model_dump(mode="json"),
    )


# Action and turn-related error handlers
async def invalid_action_error_handler(request: Request, exc: InvalidActionError) -> JSONResponse:
    """Handle invalid action errors.

    Args:
        request: The FastAPI request object
        exc: The InvalidActionError exception

    Returns:
        JSON response with error details
    """
    logger.info(f"Invalid action submitted: {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="INVALID_ACTION",
            message=str(exc),
            session_id=exc.session_id,
            details=exc.details,
        ).model_dump(mode="json"),
    )


async def invalid_turn_error_handler(request: Request, exc: InvalidTurnError) -> JSONResponse:
    """Handle invalid turn errors.

    Args:
        request: The FastAPI request object
        exc: The InvalidTurnError exception

    Returns:
        JSON response with error details
    """
    logger.info(
        f"Invalid turn number: expected {exc.expected_turn}, received {exc.received_turn}",
        extra=_sanitize_error_for_logging(exc),
    )

    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="INVALID_TURN",
            message=str(exc),
            session_id=exc.session_id,
            details={
                "expected_turn": exc.expected_turn,
                "received_turn": exc.received_turn,
            },
        ).model_dump(mode="json"),
    )


# Bot execution error handlers
async def bot_execution_error_handler(request: Request, exc: BotExecutionError) -> JSONResponse:
    """Handle bot execution errors.

    Args:
        request: The FastAPI request object
        exc: The BotExecutionError exception

    Returns:
        JSON response with error details
    """
    logger.error(f"Bot execution failed: {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="BOT_EXECUTION_ERROR",
            message=str(exc),
            session_id=exc.session_id,
        ).model_dump(mode="json"),
    )


async def bot_timeout_error_handler(request: Request, exc: BotTimeoutError) -> JSONResponse:
    """Handle bot timeout errors.

    Args:
        request: The FastAPI request object
        exc: The BotTimeoutError exception

    Returns:
        JSON response with error details
    """
    logger.warning(
        f"Bot execution timed out after {exc.timeout_seconds} seconds", extra=_sanitize_error_for_logging(exc)
    )

    return JSONResponse(
        status_code=408,
        content=TimeoutErrorResponse(
            error="BOT_TIMEOUT",
            message=str(exc),
            session_id=exc.session_id,
            timeout_seconds=exc.timeout_seconds,
            operation="bot_decision",
        ).model_dump(mode="json"),
    )


# Game engine error handler
async def game_engine_error_handler(request: Request, exc: GameEngineError) -> JSONResponse:
    """Handle game engine errors.

    Args:
        request: The FastAPI request object
        exc: The GameEngineError exception

    Returns:
        JSON response with error details
    """
    logger.error(f"Game engine error: {exc.message}", extra=_sanitize_error_for_logging(exc), exc_info=True)

    return JSONResponse(
        status_code=500,
        content=GameEngineErrorResponse(
            error="GAME_ENGINE_ERROR",
            message=str(exc),
            session_id=exc.session_id,
            details=exc.details,
        ).model_dump(mode="json"),
    )


# Database error handler
async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handle database errors.

    Args:
        request: The FastAPI request object
        exc: The DatabaseError exception

    Returns:
        JSON response with error details (sanitized for security)
    """
    logger.error(f"Database error: {exc.message}", extra=_sanitize_error_for_logging(exc), exc_info=True)

    # Don't expose internal database details to clients
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="DATABASE_ERROR",
            message="A database error occurred. Please try again later.",
        ).model_dump(mode="json"),
    )


# Validation error handler
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors.

    Args:
        request: The FastAPI request object
        exc: The ValidationError exception

    Returns:
        JSON response with error details
    """
    logger.info(f"Validation error for field '{exc.field}': {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(
            error="VALIDATION_ERROR",
            message=str(exc),
            validation_errors=[
                ValidationErrorDetail(
                    field=exc.field,
                    message=exc.message,
                )
            ],
        ).model_dump(mode="json"),
    )


# Pydantic validation error handler
async def pydantic_validation_error_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Handle Pydantic validation errors.

    Args:
        request: The FastAPI request object
        exc: The PydanticValidationError exception

    Returns:
        JSON response with validation error details
    """
    logger.info("Request validation failed", extra={"error_count": len(exc.errors())})

    validation_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        validation_errors.append(
            ValidationErrorDetail(
                field=field,
                message=error["msg"],
                invalid_value=error.get("input"),
            )
        )

    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(
            error="VALIDATION_ERROR",
            message="Request validation failed",
            validation_errors=validation_errors,
        ).model_dump(mode="json"),
    )


# SSE connection error handler
async def sse_connection_error_handler(request: Request, exc: SSEConnectionError) -> JSONResponse:
    """Handle SSE connection errors.

    Args:
        request: The FastAPI request object
        exc: The SSEConnectionError exception

    Returns:
        JSON response with error details
    """
    logger.error(f"SSE connection error: {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="SSE_CONNECTION_ERROR",
            message=str(exc),
            session_id=exc.session_id,
        ).model_dump(mode="json"),
    )


# Authorization error handler
async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    """Handle authorization errors.

    Args:
        request: The FastAPI request object
        exc: The AuthorizationError exception

    Returns:
        JSON response with error details
    """
    logger.warning(f"Authorization error: {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=403,
        content=ErrorResponse(
            error="AUTHORIZATION_ERROR",
            message=str(exc),
        ).model_dump(mode="json"),
    )


# Rate limit error handler
async def rate_limit_error_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    """Handle rate limit errors.

    Args:
        request: The FastAPI request object
        exc: The RateLimitError exception

    Returns:
        JSON response with error details
    """
    logger.warning(f"Rate limit exceeded: {exc.message}", extra=_sanitize_error_for_logging(exc))

    return JSONResponse(
        status_code=429,
        content=RateLimitErrorResponse(
            error="RATE_LIMIT_EXCEEDED",
            message=str(exc),
            retry_after_seconds=60,  # Default retry time
            limit_type="general",
        ).model_dump(mode="json"),
        headers={"Retry-After": "60"},
    )


# Configuration error handler
async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Handle configuration errors.

    Args:
        request: The FastAPI request object
        exc: The ConfigurationError exception

    Returns:
        JSON response with error details
    """
    logger.error(f"Configuration error: {exc.message}", extra=_sanitize_error_for_logging(exc), exc_info=True)

    # Don't expose internal configuration details to clients
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="CONFIGURATION_ERROR",
            message="Server configuration error. Please contact support.",
        ).model_dump(mode="json"),
    )


# General exception handler
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors.

    Args:
        request: The FastAPI request object
        exc: The Exception

    Returns:
        JSON response with generic error message
    """
    logger.error(f"Unexpected error: {type(exc).__name__}", extra={"error_type": type(exc).__name__}, exc_info=True)

    # Don't expose internal error details to clients
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
        ).model_dump(mode="json"),
    )


def register_error_handlers(app) -> None:
    """Register all exception handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    # Custom exception handlers (specific to most general)
    app.add_exception_handler(PlayerNotFoundError, player_not_found_error_handler)
    app.add_exception_handler(PlayerRegistrationError, player_registration_error_handler)
    app.add_exception_handler(SessionNotFoundError, session_not_found_error_handler)
    app.add_exception_handler(SessionAlreadyActiveError, session_already_active_error_handler)
    app.add_exception_handler(InvalidActionError, invalid_action_error_handler)
    app.add_exception_handler(InvalidTurnError, invalid_turn_error_handler)
    app.add_exception_handler(BotExecutionError, bot_execution_error_handler)
    app.add_exception_handler(BotTimeoutError, bot_timeout_error_handler)
    app.add_exception_handler(GameEngineError, game_engine_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(SSEConnectionError, sse_connection_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(RateLimitError, rate_limit_error_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)

    # Base exception handler (catches any PlaygroundError not handled above)
    app.add_exception_handler(PlaygroundError, playground_error_handler)

    # Pydantic validation errors
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)

    # General exception handler (catches everything else)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers registered successfully")
