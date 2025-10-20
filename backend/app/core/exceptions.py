"""Custom exception classes for the Spellcasters Playground Backend."""

from typing import Optional


class PlaygroundError(Exception):
    """Base exception for all playground-related errors."""

    def __init__(
        self, message: str, status_code: int = 500, session_id: Optional[str] = None, details: Optional[dict] = None
    ):
        """Initialize PlaygroundError.

        Args:
            message: Human-readable error message
            status_code: HTTP status code to return
            session_id: Related session ID (if applicable)
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.session_id = session_id
        self.details = details or {}


class PlayerNotFoundError(PlaygroundError):
    """Raised when a player is not found."""

    def __init__(self, player_id: str, **kwargs):
        super().__init__(f"Player {player_id} not found", status_code=404, **kwargs)
        self.player_id = player_id


class SessionNotFoundError(PlaygroundError):
    """Raised when a session is not found."""

    def __init__(self, session_id: str, **kwargs):
        super().__init__(f"Session {session_id} not found", status_code=404, session_id=session_id, **kwargs)


class SessionAlreadyActiveError(PlaygroundError):
    """Raised when trying to start a session that's already active."""

    def __init__(self, session_id: str, **kwargs):
        super().__init__(f"Session {session_id} is already active", status_code=409, session_id=session_id, **kwargs)


class InvalidActionError(PlaygroundError):
    """Raised when a player submits an invalid action."""

    def __init__(self, reason: str, session_id: Optional[str] = None, **kwargs):
        super().__init__(f"Invalid action: {reason}", status_code=400, session_id=session_id, **kwargs)


class InvalidTurnError(PlaygroundError):
    """Raised when action is submitted for wrong turn number."""

    def __init__(self, expected_turn: int, received_turn: int, session_id: Optional[str] = None, **kwargs):
        super().__init__(
            f"Invalid turn number. Expected {expected_turn}, received {received_turn}",
            status_code=400,
            session_id=session_id,
            **kwargs,
        )
        self.expected_turn = expected_turn
        self.received_turn = received_turn


class PlayerRegistrationError(PlaygroundError):
    """Raised when player registration fails."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(f"Player registration failed: {reason}", status_code=400, **kwargs)


class BotExecutionError(PlaygroundError):
    """Raised when bot code execution fails."""

    def __init__(self, reason: str, session_id: Optional[str] = None, **kwargs):
        super().__init__(f"Bot execution error: {reason}", status_code=500, session_id=session_id, **kwargs)


class BotTimeoutError(PlaygroundError):
    """Raised when bot execution times out."""

    def __init__(self, timeout_seconds: float, session_id: Optional[str] = None, **kwargs):
        super().__init__(
            f"Bot execution timed out after {timeout_seconds} seconds", status_code=408, session_id=session_id, **kwargs
        )
        self.timeout_seconds = timeout_seconds


class GameEngineError(PlaygroundError):
    """Raised when game engine encounters an error."""

    def __init__(self, reason: str, session_id: Optional[str] = None, **kwargs):
        super().__init__(f"Game engine error: {reason}", status_code=500, session_id=session_id, **kwargs)


class DatabaseError(PlaygroundError):
    """Raised when database operations fail."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(f"Database error: {reason}", status_code=500, **kwargs)


class ValidationError(PlaygroundError):
    """Raised when input validation fails."""

    def __init__(self, field: str, reason: str, **kwargs):
        super().__init__(f"Validation error for field '{field}': {reason}", status_code=422, **kwargs)
        self.field = field


class SSEConnectionError(PlaygroundError):
    """Raised when SSE connection fails."""

    def __init__(self, reason: str, session_id: Optional[str] = None, **kwargs):
        super().__init__(f"SSE connection error: {reason}", status_code=500, session_id=session_id, **kwargs)


class AuthorizationError(PlaygroundError):
    """Raised when user is not authorized for an action."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(f"Authorization error: {reason}", status_code=403, **kwargs)


class RateLimitError(PlaygroundError):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: str, **kwargs):
        super().__init__(f"Rate limit exceeded: {limit}", status_code=429, **kwargs)


class ConfigurationError(PlaygroundError):
    """Raised when configuration is invalid."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(f"Configuration error: {reason}", status_code=500, **kwargs)


class PlayerAlreadyInLobbyError(PlaygroundError):
    """Raised when a player tries to join lobby while already in queue."""

    def __init__(self, player_id: str, **kwargs):
        super().__init__(f"Player {player_id} is already in lobby queue", status_code=409, **kwargs)
        self.player_id = player_id
