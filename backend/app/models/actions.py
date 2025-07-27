"""Action models for player actions in the Spellcasters Playground Backend."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SpellAction(BaseModel):
    """Represents a spell action."""
    name: str = Field(..., description="Spell name")
    target: Optional[List[int]] = Field(default=None, description="Spell target coordinates [x, y]")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {"name": "fireball", "target": [5, 3]},
                {"name": "heal", "target": None},
                {"name": "shield", "target": None}
            ]
        }


class MoveResult(BaseModel):
    """Result of a player's move."""
    success: bool = Field(..., description="Whether the move was successful")
    damage_dealt: int = Field(default=0, description="Damage dealt to opponent")
    damage_received: int = Field(default=0, description="Damage received")
    position_after: List[int] = Field(..., description="Position after move [x, y]")
    events: List[str] = Field(default_factory=list, description="Descriptive events for this move")
    mana_used: int = Field(default=0, description="Mana consumed by this action")
    hp_after: int = Field(..., description="HP after this action")
    mana_after: int = Field(..., description="Mana after this action")


class Move(BaseModel):
    """Represents a complete move made by a player in a single turn."""
    player_id: str = Field(..., description="Player who made the move")
    turn: int = Field(..., description="Turn number")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the move was made")
    move: Optional[List[int]] = Field(default=None, description="Movement delta [dx, dy]")
    spell: Optional[SpellAction] = Field(default=None, description="Spell action (if any)")
    result: Optional[MoveResult] = Field(default=None, description="Result of the move (set after processing)")


class PlayerAction(BaseModel):
    """Request model for player action submission."""
    player_id: str = Field(..., description="Player submitting the action")
    turn: int = Field(..., description="Expected turn number")
    action_data: Dict[str, Any] = Field(..., description="Action data (move, spell, etc.)")
    
    def to_move(self) -> Move:
        """Convert PlayerAction to Move object."""
        return Move(
            player_id=self.player_id,
            turn=self.turn,
            move=self.action_data.get("move"),
            spell=SpellAction(**self.action_data["spell"]) if self.action_data.get("spell") else None
        )


class ActionData(BaseModel):
    """Raw action data format expected from bots."""
    move: Optional[List[int]] = Field(default=None, description="Movement [dx, dy]")
    spell: Optional[Dict[str, Any]] = Field(default=None, description="Spell action")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {"move": [1, 0], "spell": None},
                {"move": None, "spell": {"name": "fireball", "target": [5, 3]}},
                {"move": [0, 1], "spell": {"name": "heal"}}
            ]
        }


class MoveHistory(BaseModel):
    """Complete move history for a game session."""
    session_id: str = Field(..., description="Session identifier")
    moves: List[Move] = Field(default_factory=list, description="All moves in chronological order")
    total_turns: int = Field(default=0, description="Total number of turns completed")
    
    def add_move(self, move: Move) -> None:
        """Add a move to the history."""
        self.moves.append(move)
        if move.turn > self.total_turns:
            self.total_turns = move.turn
    
    def get_moves_by_player(self, player_id: str) -> List[Move]:
        """Get all moves for a specific player."""
        return [move for move in self.moves if move.player_id == player_id]
    
    def get_moves_by_turn(self, turn: int) -> List[Move]:
        """Get all moves for a specific turn."""
        return [move for move in self.moves if move.turn == turn]
    
    def get_last_turn_moves(self) -> List[Move]:
        """Get moves from the most recent turn."""
        if self.total_turns == 0:
            return []
        return self.get_moves_by_turn(self.total_turns)


class TurnActionCollection(BaseModel):
    """Collection of actions for a single turn."""
    turn: int = Field(..., description="Turn number")
    actions: Dict[str, Move] = Field(default_factory=dict, description="Actions by player_id")
    collected_at: datetime = Field(default_factory=datetime.now, description="When collection was completed")
    timeout_occurred: bool = Field(default=False, description="Whether timeout occurred")
    
    def add_action(self, player_id: str, move: Move) -> None:
        """Add a player's action to the collection."""
        self.actions[player_id] = move
    
    def is_complete(self, expected_players: List[str]) -> bool:
        """Check if all expected players have submitted actions."""
        return all(player_id in self.actions for player_id in expected_players)
    
    def get_missing_players(self, expected_players: List[str]) -> List[str]:
        """Get list of players who haven't submitted actions."""
        return [player_id for player_id in expected_players if player_id not in self.actions] 