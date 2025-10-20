"""Bot interface and models for the Spellcasters Playground Backend."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .players import Player, PlayerRegistration
from .actions import ActionData


class BotInterface(ABC):
    """
    Standardized interface for all bots (built-in and player).
    Encapsulates in-game execution: game strategy, turn actions etc.
    Maintains strong one-directional reference to Player instance.
    """

    def __init__(self, player: Player):
        """Initialize bot with reference to Player instance."""
        self._player = player

    @property
    def player(self) -> Player:
        """Get the Player instance this bot represents."""
        return self._player

    @property
    def name(self) -> str:
        """Bot identification name (delegates to player)."""
        return self._player.player_name

    @property
    def player_id(self) -> str:
        """Unique player ID (delegates to player)."""
        return self._player.player_id

    @abstractmethod
    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main decision method called by game engine.

        Args:
            state: Current game state from the game engine

        Returns:
            Action dictionary with format: {"move": [dx, dy], "spell": {...}}
        """
        pass

    @property
    def is_builtin(self) -> bool:
        """Flag indicating if this is a built-in bot."""
        return self._player.is_builtin


class BotCreationRequest(BaseModel):
    """Request to create a new player bot."""

    bot_code: str = Field(..., description="Python code for the bot implementation")
    player_id: Optional[str] = Field(default=None, description="Existing player ID to reuse")
    player_registration: Optional[PlayerRegistration] = Field(default=None, description="New player registration data")

    def model_validate(self, values):
        """Validate that either player_id or player_registration is provided."""
        if not values.get("player_id") and not values.get("player_registration"):
            raise ValueError("Must provide either player_id or player_registration")
        return values


class BotInfo(BaseModel):
    """Information about available bots."""

    bot_type: Literal["builtin", "player"] = Field(..., description="Type of bot")
    bot_id: str = Field(..., description="Unique bot identifier")
    player_id: str = Field(..., description="Associated player ID")
    player_name: str = Field(..., description="Player display name")
    description: Optional[str] = Field(default=None, description="Bot description")
    difficulty: Optional[str] = Field(default=None, description="Difficulty level for built-in bots")


class PlayerBot(BotInterface):
    """
    Remote player bot implementation.
    Waits for action submission via HTTP API endpoint and returns the submitted action.
    Encapsulates in-game execution with strong reference to Player instance.
    """

    def __init__(self, player: Player):
        """Initialize with Player instance."""
        super().__init__(player)
        self._last_action: Optional[ActionData] = None

    def set_action(self, action: ActionData) -> None:
        """Store the action submitted via HTTP API for the next turn."""
        self._last_action = action

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Return the last submitted action, or no-op if none submitted.

        Note: The action is cleared after being returned to prevent reuse.
        Each turn requires a fresh action submission.
        """
        if self._last_action is None:
            return {"move": [0, 0], "spell": None}

        action = self._last_action
        self._last_action = None  # Clear action after use to prevent reuse

        # Convert ActionData to game engine format
        result = {"move": action.move if action.move else [0, 0], "spell": None}

        if action.spell:
            result["spell"] = action.spell

        return result


class HumanBot(BotInterface):
    """Human-controlled bot that plays the last submitted action."""

    def __init__(self, player: Player):
        super().__init__(player)
        self._last_action: Optional[ActionData] = None

    def set_action(self, action: ActionData) -> None:
        self._last_action = action

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Return the last submitted action, or no-op if none submitted.

        Note: The action is cleared after being returned to prevent reuse.
        Each turn requires a fresh action submission.
        """
        if self._last_action is None:
            return {"move": [0, 0], "spell": None}

        action = self._last_action
        self._last_action = None  # Clear action after use to prevent reuse

        return {"move": action.move, "spell": action.spell}


class PlayerBotFactory:
    """Factory for creating player bots with proper player references."""

    @staticmethod
    def create_bot(request: BotCreationRequest, player_registry) -> PlayerBot:
        """
        Create a player bot with reference to existing or new player.

        User can choose to:
        1. Reuse existing Player (provide player_id)
        2. Register new Player (provide player_registration) - fresh stats

        Note: bot_code parameter in BotCreationRequest is deprecated and ignored.
        PlayerBot now waits for action submission via HTTP API.

        Args:
            request: Bot creation request with player info
            player_registry: Registry to get/create players

        Returns:
            PlayerBot instance with proper player reference

        Raises:
            ValueError: If player not found or invalid request
        """
        if request.player_id:
            # Option 1: Reuse existing player
            player = player_registry.get_player(request.player_id)
            if not player:
                raise ValueError(f"Player {request.player_id} not found")
        elif request.player_registration:
            # Option 2: Register new player for fresh stats
            player = player_registry.register_player(request.player_registration)
        else:
            raise ValueError("Must provide either player_id or player_registration")

        # Create PlayerBot for remote action submission
        return PlayerBot(player)
