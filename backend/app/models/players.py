"""Player models for the Spellcasters Playground Backend."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlayerRegistration(BaseModel):
    """Request model for player registration."""

    player_name: str = Field(..., min_length=1, max_length=50, description="Player display name")
    submitted_from: Literal["online", "upload"] = Field(default="online", description="How the bot was submitted")
    sprite_path: Optional[str] = Field(default=None, description="Path to player sprite image")
    minion_sprite_path: Optional[str] = Field(default=None, description="Path to player minion sprite image")


class Player(BaseModel):
    """Player model with complete player information and statistics."""

    player_id: str = Field(..., description="Unique player identifier (UUID)")
    player_name: str = Field(..., description="Player display name")
    submitted_from: str = Field(..., description="How the bot was submitted")
    sprite_path: Optional[str] = Field(default=None, description="Path to player sprite image")
    minion_sprite_path: Optional[str] = Field(default=None, description="Path to player minion sprite image")
    total_matches: int = Field(default=0, description="Total number of matches played")
    wins: int = Field(default=0, description="Number of wins")
    losses: int = Field(default=0, description="Number of losses")
    draws: int = Field(default=0, description="Number of draws")
    created_at: datetime = Field(default_factory=datetime.now, description="Player registration timestamp")
    is_builtin: bool = Field(default=False, description="True for built-in players")

    @property
    def win_rate(self) -> float:
        """Calculate win rate as a percentage."""
        if self.total_matches == 0:
            return 0.0
        return (self.wins / self.total_matches) * 100.0

    def update_stats(self, result: str) -> None:
        """Update player statistics based on match result."""
        self.total_matches += 1
        if result == "win":
            self.wins += 1
        elif result == "loss":
            self.losses += 1
        elif result == "draw":
            self.draws += 1


class PlayerConfig(BaseModel):
    """Configuration for players in a game session."""

    player_id: str = Field(..., description="Player ID to use in the session")
    bot_type: Literal["builtin", "player"] = Field(..., description="Type of bot")
    bot_id: Optional[str] = Field(default=None, description="Bot ID for built-in bots")
    is_human: bool = Field(default=False, description="True if this is a human player using SSE")
