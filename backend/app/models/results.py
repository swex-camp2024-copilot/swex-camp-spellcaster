"""Result models for game outcomes in the Spellcasters Playground Backend."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class GameResultType(str, Enum):
    """Enumeration of possible game result types."""
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"


class PlayerGameStats(BaseModel):
    """Individual player statistics for a completed game."""
    player_id: str = Field(..., description="Player identifier")
    player_name: str = Field(..., description="Player display name")
    final_hp: int = Field(..., description="Final hit points")
    final_mana: int = Field(..., description="Final mana")
    final_position: List[int] = Field(..., description="Final position [x, y]")
    damage_dealt: int = Field(default=0, description="Total damage dealt")
    damage_received: int = Field(default=0, description="Total damage received")
    spells_cast: int = Field(default=0, description="Number of spells cast")
    artifacts_collected: int = Field(default=0, description="Number of artifacts collected")
    turns_played: int = Field(default=0, description="Number of turns participated")
    
    @property
    def survived(self) -> bool:
        """Check if player survived the match."""
        return self.final_hp > 0


class GameResult(BaseModel):
    """Complete game result with all details."""
    session_id: str = Field(..., description="Session identifier")
    winner: Optional[str] = Field(default=None, description="Winner player ID (None for draw)")
    loser: Optional[str] = Field(default=None, description="Loser player ID (None for draw)")
    result_type: GameResultType = Field(..., description="Type of result")
    total_rounds: int = Field(..., description="Total number of rounds/turns played")
    first_player: str = Field(..., description="Player ID who went first")
    game_duration: float = Field(..., description="Game duration in seconds")
    final_scores: Dict[str, PlayerGameStats] = Field(..., description="Final statistics for each player")
    end_condition: str = Field(..., description="How the game ended")
    created_at: datetime = Field(default_factory=datetime.now, description="Result timestamp")
    
    def get_player_stats(self, player_id: str) -> Optional[PlayerGameStats]:
        """Get statistics for a specific player."""
        return self.final_scores.get(player_id)
    
    def get_winner_stats(self) -> Optional[PlayerGameStats]:
        """Get statistics for the winner."""
        if self.winner:
            return self.final_scores.get(self.winner)
        return None
    
    def get_loser_stats(self) -> Optional[PlayerGameStats]:
        """Get statistics for the loser."""
        if self.loser:
            return self.final_scores.get(self.loser)
        return None
    
    def determine_result_for_player(self, player_id: str) -> GameResultType:
        """Determine the result type from a specific player's perspective."""
        if self.result_type == GameResultType.DRAW:
            return GameResultType.DRAW
        elif self.winner == player_id:
            return GameResultType.WIN
        else:
            return GameResultType.LOSS


class MatchOutcome(BaseModel):
    """Simple match outcome model for quick results."""
    session_id: str = Field(..., description="Session identifier")
    winner_id: Optional[str] = Field(default=None, description="Winner player ID")
    winner_name: Optional[str] = Field(default=None, description="Winner player name")
    loser_id: Optional[str] = Field(default=None, description="Loser player ID")
    loser_name: Optional[str] = Field(default=None, description="Loser player name")
    is_draw: bool = Field(default=False, description="Whether the match was a draw")
    end_condition: str = Field(..., description="How the match ended")
    total_turns: int = Field(..., description="Total turns played")
    duration_seconds: float = Field(..., description="Match duration in seconds")


class PlayerMatchResult(BaseModel):
    """Player-specific match result for statistics updates."""
    player_id: str = Field(..., description="Player identifier")
    result: GameResultType = Field(..., description="Result from this player's perspective")
    opponent_id: str = Field(..., description="Opponent player identifier")
    session_id: str = Field(..., description="Session identifier")
    stats: PlayerGameStats = Field(..., description="Player's game statistics")
    match_date: datetime = Field(default_factory=datetime.now, description="When the match completed") 