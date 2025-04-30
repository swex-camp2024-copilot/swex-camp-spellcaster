from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class BotRegistration(BaseModel):
    """Model for bot initial registration with the game engine."""
    name: str
    sprite_path: Optional[str] = None
    minion_sprite_path: Optional[str] = None


class GameState(BaseModel):
    """Model representing game state sent to bots."""
    turn: int
    board_size: int
    self: Dict[str, Any]
    opponent: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    minions: List[Dict[str, Any]]


class BotAction(BaseModel):
    """Model for bot decisions."""
    move: List[int]
    spell: Optional[Dict[str, Any]] = None


class BotInterface(ABC):
    """Abstract base class for bots to implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the bot's name."""
        pass

    @property
    def sprite_path(self) -> Optional[str]:
        """Return path to wizard sprite (optional)."""
        return None

    @property
    def minion_sprite_path(self) -> Optional[str]:
        """Return path to minion sprite (optional)."""
        return None

    @abstractmethod
    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process game state and return action decision."""
        pass

    def get_registration(self) -> BotRegistration:
        """Get bot registration data."""
        return BotRegistration(
            name=self.name,
            sprite_path=self.sprite_path,
            minion_sprite_path=self.minion_sprite_path
        )