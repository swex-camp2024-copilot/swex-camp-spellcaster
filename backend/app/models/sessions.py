"""Session models for the Spellcasters Playground Backend."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TurnStatus(str, Enum):
    """Enumeration of possible turn statuses."""

    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlayerSlot(BaseModel):
    """Represents a player slot in a game session."""

    player_id: str = Field(..., description="Player ID participating in the session")
    player_name: str = Field(..., description="Player display name")
    is_builtin_bot: bool = Field(default=False, description="True if this is a built-in bot")
    connection_handle: Optional[str] = Field(default=None, description="SSE connection ID for human players")
    last_action_timestamp: Optional[datetime] = Field(default=None, description="Timestamp of last action")

    # Game state fields (to be updated from game engine)
    hp: Optional[int] = Field(default=None, description="Current hit points")
    mana: Optional[int] = Field(default=None, description="Current mana")
    position: Optional[List[int]] = Field(default=None, description="Current position [x, y]")


class GameState(BaseModel):
    """Complete game session state."""

    session_id: str = Field(..., description="Unique session identifier")
    player_1: PlayerSlot = Field(..., description="Player 1 slot")
    player_2: PlayerSlot = Field(..., description="Player 2 slot")
    current_game_state: Dict[str, Any] = Field(default_factory=dict, description="Current game engine state")
    match_log: List[str] = Field(default_factory=list, description="Match event log")
    turn_index: int = Field(default=0, description="Current turn number")
    status: TurnStatus = Field(default=TurnStatus.WAITING, description="Current session status")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation timestamp")
    last_activity: datetime = Field(default_factory=datetime.now, description="Last activity timestamp")
    winner_id: Optional[str] = Field(default=None, description="Winner player ID (if game is complete)")

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()

    def add_log_entry(self, message: str) -> None:
        """Add an entry to the match log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.match_log.append(f"[{timestamp}] {message}")
        self.update_activity()

    def get_player_slot(self, player_id: str) -> Optional[PlayerSlot]:
        """Get player slot by player ID."""
        if self.player_1.player_id == player_id:
            return self.player_1
        elif self.player_2.player_id == player_id:
            return self.player_2
        return None

    def get_opponent_slot(self, player_id: str) -> Optional[PlayerSlot]:
        """Get opponent slot for a given player ID."""
        if self.player_1.player_id == player_id:
            return self.player_2
        elif self.player_2.player_id == player_id:
            return self.player_1
        return None


class SessionCreationRequest(BaseModel):
    """Request model for creating a new game session."""

    player_1_config: Dict[str, Any] = Field(..., description="Player 1 configuration")
    player_2_config: Dict[str, Any] = Field(..., description="Player 2 configuration")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Optional game settings override")
    visualize: bool = Field(default=False, description="Enable pygame visualization for this session")


class SessionInfo(BaseModel):
    """Basic session information for API responses."""

    session_id: str = Field(..., description="Session identifier")
    player_1_name: str = Field(..., description="Player 1 name")
    player_2_name: str = Field(..., description="Player 2 name")
    status: TurnStatus = Field(..., description="Current session status")
    turn_index: int = Field(..., description="Current turn number")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_activity: datetime = Field(..., description="Last activity timestamp")
