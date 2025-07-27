"""SQLModel database models for persistence in the Spellcasters Playground Backend."""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class PlayerDB(SQLModel, table=True):
    """Database model for persistent player storage."""
    __tablename__ = "players"
    
    player_id: str = Field(primary_key=True, description="Unique player identifier")
    player_name: str = Field(index=True, description="Player display name")
    submitted_from: str = Field(description="How the bot was submitted")
    sprite_path: Optional[str] = Field(default=None, description="Path to player sprite image")
    minion_sprite_path: Optional[str] = Field(default=None, description="Path to player minion sprite image")
    total_matches: int = Field(default=0, description="Total number of matches played")
    wins: int = Field(default=0, description="Number of wins")
    losses: int = Field(default=0, description="Number of losses")
    draws: int = Field(default=0, description="Number of draws")
    created_at: datetime = Field(default_factory=datetime.now, description="Player registration timestamp")
    is_builtin: bool = Field(default=False, description="True for built-in players")
    
    # Relationships
    sessions_as_player_1: List["SessionDB"] = Relationship(
        back_populates="player_1",
        sa_relationship_kwargs={"foreign_keys": "SessionDB.player_1_id"}
    )
    sessions_as_player_2: List["SessionDB"] = Relationship(
        back_populates="player_2", 
        sa_relationship_kwargs={"foreign_keys": "SessionDB.player_2_id"}
    )
    game_results_as_winner: List["GameResultDB"] = Relationship(
        back_populates="winner",
        sa_relationship_kwargs={"foreign_keys": "GameResultDB.winner_id"}
    )
    game_results_as_loser: List["GameResultDB"] = Relationship(
        back_populates="loser",
        sa_relationship_kwargs={"foreign_keys": "GameResultDB.loser_id"}
    )
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate as a percentage."""
        if self.total_matches == 0:
            return 0.0
        return (self.wins / self.total_matches) * 100.0


class SessionDB(SQLModel, table=True):
    """Database model for session persistence."""
    __tablename__ = "sessions"
    
    session_id: str = Field(primary_key=True, description="Unique session identifier")
    player_1_id: str = Field(foreign_key="players.player_id", description="Player 1 ID")
    player_2_id: str = Field(foreign_key="players.player_id", description="Player 2 ID")
    status: str = Field(description="Current session status")
    turn_index: int = Field(default=0, description="Current turn number")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Session completion timestamp")
    winner_id: Optional[str] = Field(default=None, description="Winner player ID (if completed)")
    
    # Relationships
    player_1: PlayerDB = Relationship(
        back_populates="sessions_as_player_1",
        sa_relationship_kwargs={"foreign_keys": "SessionDB.player_1_id"}
    )
    player_2: PlayerDB = Relationship(
        back_populates="sessions_as_player_2",
        sa_relationship_kwargs={"foreign_keys": "SessionDB.player_2_id"}
    )
    game_result: Optional["GameResultDB"] = Relationship(back_populates="session")
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Calculate session duration in minutes."""
        if self.completed_at:
            delta = self.completed_at - self.created_at
            return delta.total_seconds() / 60.0
        else:
            delta = datetime.now() - self.created_at
            return delta.total_seconds() / 60.0


class GameResultDB(SQLModel, table=True):
    """Database model for persistent game results."""
    __tablename__ = "game_results"
    
    session_id: str = Field(primary_key=True, foreign_key="sessions.session_id", description="Session identifier")
    winner_id: Optional[str] = Field(
        foreign_key="players.player_id", 
        default=None, 
        description="Winner player ID (None for draw)"
    )
    loser_id: Optional[str] = Field(
        foreign_key="players.player_id",
        default=None, 
        description="Loser player ID (None for draw)"
    )
    result_type: str = Field(description="Type of result (win/loss/draw)")
    total_rounds: int = Field(description="Total number of rounds/turns played")
    game_duration: float = Field(description="Game duration in seconds")
    end_condition: str = Field(description="How the game ended")
    
    # Player statistics (stored as JSON-like text fields for simplicity)
    player_1_final_hp: Optional[int] = Field(default=None, description="Player 1 final HP")
    player_1_final_mana: Optional[int] = Field(default=None, description="Player 1 final mana")
    player_1_damage_dealt: int = Field(default=0, description="Player 1 damage dealt")
    player_1_damage_received: int = Field(default=0, description="Player 1 damage received")
    player_1_spells_cast: int = Field(default=0, description="Player 1 spells cast")
    
    player_2_final_hp: Optional[int] = Field(default=None, description="Player 2 final HP")
    player_2_final_mana: Optional[int] = Field(default=None, description="Player 2 final mana")
    player_2_damage_dealt: int = Field(default=0, description="Player 2 damage dealt")
    player_2_damage_received: int = Field(default=0, description="Player 2 damage received")
    player_2_spells_cast: int = Field(default=0, description="Player 2 spells cast")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Result timestamp")
    
    # Relationships
    session: SessionDB = Relationship(back_populates="game_result")
    winner: Optional[PlayerDB] = Relationship(
        back_populates="game_results_as_winner",
        sa_relationship_kwargs={"foreign_keys": "GameResultDB.winner_id"}
    )
    loser: Optional[PlayerDB] = Relationship(
        back_populates="game_results_as_loser",
        sa_relationship_kwargs={"foreign_keys": "GameResultDB.loser_id"}
    ) 