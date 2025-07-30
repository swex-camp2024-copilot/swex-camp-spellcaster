"""Bot interface and models for the Spellcasters Playground Backend."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .players import Player, PlayerRegistration


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
    player_registration: Optional[PlayerRegistration] = Field(
        default=None, 
        description="New player registration data"
    )

    def model_validate(self, values):
        """Validate that either player_id or player_registration is provided."""
        if not values.get('player_id') and not values.get('player_registration'):
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
    Player-submitted bot implementation.
    Encapsulates in-game execution with strong reference to Player instance.
    """

    def __init__(self, player: Player, bot_code: str):
        """Initialize with Player instance and bot code."""
        super().__init__(player)
        self._bot_code = bot_code
        self._compiled_code = None
        self._compile_bot_code()

    def _compile_bot_code(self) -> None:
        """Compile and validate the bot code."""
        try:
            # Compile the bot code to check for syntax errors
            self._compiled_code = compile(self._bot_code, f"<bot_{self.player_id}>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Bot code has syntax errors: {e}")

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute player's bot code with the given game state."""
        if not self._compiled_code:
            raise RuntimeError("Bot code not compiled")

        # Create a safe execution environment
        bot_globals = {
            "__builtins__": {
                "len": len,
                "range": range,
                "min": min,
                "max": max,
                "abs": abs,
                "sum": sum,
                "sorted": sorted,
                "enumerate": enumerate,
                "zip": zip,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
            }
        }
        bot_locals = {"state": state}

        try:
            # Execute the bot code
            exec(self._compiled_code, bot_globals, bot_locals)
            
            # The bot code should define a 'decide' function that returns the action
            if "decide" not in bot_locals:
                raise ValueError("Bot code must define a 'decide' function")
            
            decide_func = bot_locals["decide"]
            if not callable(decide_func):
                raise ValueError("'decide' must be a function")
            
            # Call the bot's decide function
            action = decide_func(state)
            
            # Validate action format
            if not isinstance(action, dict):
                raise ValueError("Bot decision must return a dictionary")
            
            return action
            
        except Exception as e:
            # Log the error and return a safe default action
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Bot {self.player_id} execution error: {e}")
            
            # Return a safe default action (no move, no spell)
            return {"move": [0, 0], "spell": None}


class PlayerBotFactory:
    """Factory for creating player bots with proper player references."""

    @staticmethod
    def create_bot(request: BotCreationRequest, player_registry) -> PlayerBot:
        """
        Create a player bot with reference to existing or new player.
        
        User can choose to:
        1. Reuse existing Player (provide player_id)
        2. Register new Player (provide player_registration) - fresh stats
        
        Args:
            request: Bot creation request with code and player info
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

        return PlayerBot(player, request.bot_code)