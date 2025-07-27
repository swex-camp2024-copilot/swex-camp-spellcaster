"""Error response models for the Spellcasters Playground Backend."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorResponse(BaseModel):
    """Standard error response model for all API endpoints."""
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    session_id: Optional[str] = Field(default=None, description="Related session ID (if applicable)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "error": "SESSION_NOT_FOUND",
                    "message": "Session abc123 not found",
                    "session_id": "abc123",
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                {
                    "error": "INVALID_ACTION",
                    "message": "Invalid action: move out of bounds",
                    "details": {"position": [10, 5], "board_size": [8, 8]},
                    "session_id": "def456",
                    "timestamp": "2024-01-15T10:31:00Z"
                }
            ]
        }


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information."""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    invalid_value: Optional[Any] = Field(default=None, description="The invalid value that was provided")


class ValidationErrorResponse(ErrorResponse):
    """Extended error response for validation errors."""
    validation_errors: list[ValidationErrorDetail] = Field(
        default_factory=list,
        description="Detailed validation error information"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "validation_errors": [
                    {
                        "field": "player_name",
                        "message": "Field is required",
                        "invalid_value": None
                    },
                    {
                        "field": "action_data.move",
                        "message": "Must be a list of 2 integers",
                        "invalid_value": [1, 2, 3]
                    }
                ],
                "timestamp": "2024-01-15T10:32:00Z"
            }
        }


class TimeoutErrorResponse(ErrorResponse):
    """Error response for timeout-related errors."""
    timeout_seconds: float = Field(..., description="Timeout duration in seconds")
    operation: str = Field(..., description="Operation that timed out")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "BOT_TIMEOUT",
                "message": "Bot execution timed out after 5.0 seconds",
                "timeout_seconds": 5.0,
                "operation": "bot_decision",
                "session_id": "abc123",
                "timestamp": "2024-01-15T10:33:00Z"
            }
        }


class RateLimitErrorResponse(ErrorResponse):
    """Error response for rate limiting."""
    retry_after_seconds: Optional[int] = Field(default=None, description="Seconds to wait before retrying")
    limit_type: str = Field(..., description="Type of rate limit that was exceeded")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Action submission rate limit exceeded",
                "retry_after_seconds": 60,
                "limit_type": "action_submission",
                "timestamp": "2024-01-15T10:34:00Z"
            }
        }


class GameEngineErrorResponse(ErrorResponse):
    """Error response for game engine-related errors."""
    game_state: Optional[Dict[str, Any]] = Field(default=None, description="Game state when error occurred")
    turn_number: Optional[int] = Field(default=None, description="Turn number when error occurred")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "GAME_ENGINE_ERROR",
                "message": "Invalid spell target coordinates",
                "details": {"spell": "fireball", "target": [10, 10], "max_range": 5},
                "turn_number": 15,
                "session_id": "abc123",
                "timestamp": "2024-01-15T10:35:00Z"
            }
        } 