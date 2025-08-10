"""Event models for Server-Sent Events (SSE) in the Spellcasters Playground Backend."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class TurnEvent(BaseModel):
    """SSE event for turn updates."""

    event: Literal["turn_update"] = Field(default="turn_update", description="Event type")
    turn: int = Field(..., description="Turn number")
    game_state: Dict[str, Any] = Field(..., description="Current game state")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Player actions for this turn")
    events: List[str] = Field(default_factory=list, description="Descriptive events for this turn")
    log_line: str = Field(..., description="Log line for this turn")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


class GameOverEvent(BaseModel):
    """SSE event for game completion."""

    event: Literal["game_over"] = Field(default="game_over", description="Event type")
    winner: Optional[str] = Field(default=None, description="Winner player ID (None for draw)")
    winner_name: Optional[str] = Field(default=None, description="Winner player name")
    final_state: Dict[str, Any] = Field(..., description="Final game state")
    game_result: Dict[str, Any] = Field(..., description="Complete game result")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


class ReplayTurnEvent(BaseModel):
    """SSE event for replaying a previously emitted turn (no delays)."""

    event: Literal["replay_turn"] = Field(default="replay_turn", description="Event type")
    turn: int = Field(..., description="Turn number")
    game_state: Dict[str, Any] = Field(..., description="Game state at the time of the turn")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Player actions for this turn")
    events: List[str] = Field(default_factory=list, description="Descriptive events for this turn")
    log_line: str = Field(..., description="Log line for this turn")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


class HeartbeatEvent(BaseModel):
    """SSE heartbeat event to keep connection alive."""

    event: Literal["heartbeat"] = Field(default="heartbeat", description="Event type")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


class ErrorEvent(BaseModel):
    """SSE event for error notifications."""

    event: Literal["error"] = Field(default="error", description="Event type")
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    session_id: Optional[str] = Field(default=None, description="Related session ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


class SessionStartEvent(BaseModel):
    """SSE event for session start notification."""

    event: Literal["session_start"] = Field(default="session_start", description="Event type")
    session_id: str = Field(..., description="Session identifier")
    player_1_name: str = Field(..., description="Player 1 name")
    player_2_name: str = Field(..., description="Player 2 name")
    initial_state: Dict[str, Any] = Field(..., description="Initial game state")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


# Union type for all possible events
Event = Union[TurnEvent, GameOverEvent, HeartbeatEvent, ErrorEvent, SessionStartEvent, ReplayTurnEvent]


class SSEConnection(BaseModel):
    """Represents an SSE connection."""

    connection_id: str = Field(..., description="Unique connection identifier")
    session_id: str = Field(..., description="Associated session ID")
    player_id: Optional[str] = Field(default=None, description="Associated player ID (if any)")
    connected_at: datetime = Field(default_factory=datetime.now, description="Connection timestamp")
    last_ping: datetime = Field(default_factory=datetime.now, description="Last heartbeat timestamp")

    def update_ping(self) -> None:
        """Update the last ping timestamp."""
        self.last_ping = datetime.now()

    def is_stale(self, timeout_seconds: float = 60.0) -> bool:
        """Check if connection is stale based on last ping."""
        elapsed = (datetime.now() - self.last_ping).total_seconds()
        return elapsed > timeout_seconds
