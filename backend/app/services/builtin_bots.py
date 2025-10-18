"""Built-in bot registry and factory for the Spellcasters Playground Backend."""

import logging
from datetime import datetime
from typing import Dict, List, Any

from ..models.bots import BotInterface, BotInfo
from ..models.players import Player

logger = logging.getLogger(__name__)


class BuiltinBotWrapper(BotInterface):
    """
    Wrapper that adapts existing bots to the new BotInterface.
    This allows us to use existing bot implementations with the new player reference system.
    """

    def __init__(self, player: Player, original_bot_class):
        """Initialize wrapper with player reference and original bot class."""
        super().__init__(player)
        self._original_bot = original_bot_class()

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate decision to the original bot implementation."""
        try:
            return self._original_bot.decide(state)
        except Exception as e:
            logger.error(f"Built-in bot {self.name} execution error: {e}")
            # Return safe default action
            return {"move": [0, 0], "spell": None}


class BuiltinBotRegistry:
    """Registry and factory for built-in bots with their default players."""

    # Built-in players (hard-coded)
    BUILTIN_PLAYERS = {
        "builtin_sample_1": Player(
            player_id="builtin_sample_1",
            player_name="Sample Bot 1",
            submitted_from="builtin",
            sprite_path="assets/wizards/sample_bot1.png",
            minion_sprite_path="assets/minions/minion_1.png",
            is_builtin=True,
            created_at=datetime.now(),
        ),
        "builtin_sample_2": Player(
            player_id="builtin_sample_2",
            player_name="Sample Bot 2",
            submitted_from="builtin",
            sprite_path="assets/wizards/sample_bot2.png",
            minion_sprite_path="assets/minions/minion_2.png",
            is_builtin=True,
            created_at=datetime.now(),
        ),
        "builtin_sample_3": Player(
            player_id="builtin_sample_3",
            player_name="Sample Bot 3",
            submitted_from="builtin",
            sprite_path="assets/wizards/sample_bot3.png",
            minion_sprite_path="assets/minions/minion_3.png",
            is_builtin=True,
            created_at=datetime.now(),
        ),
        "builtin_tactical": Player(
            player_id="builtin_tactical",
            player_name="Tactical Bot",
            submitted_from="builtin",
            sprite_path="assets/wizards/tactical_bot.png",
            minion_sprite_path="assets/minions/tactical_minion.png",
            is_builtin=True,
            created_at=datetime.now(),
        ),
        "builtin_rincewind": Player(
            player_id="builtin_rincewind",
            player_name="Rincewind Bot",
            submitted_from="builtin",
            sprite_path="assets/wizards/rincewind.png",
            minion_sprite_path="assets/minions/minion_1.png",
            is_builtin=True,
            created_at=datetime.now(),
        ),
        "builtin_ai": Player(
            player_id="builtin_ai",
            player_name="AI Bot",
            submitted_from="builtin",
            sprite_path="assets/wizards/ai_bot.png",
            minion_sprite_path="assets/minions/ai_minion.png",
            is_builtin=True,
            created_at=datetime.now(),
        ),
    }

    # Built-in bot configurations
    BUILTIN_BOTS = {
        "sample_bot_1": {
            "player_id": "builtin_sample_1",
            "bot_module": "bots.sample_bot1.sample_bot_1",
            "bot_class": "SampleBot1",
            "difficulty": "easy",
            "description": "A simple bot for beginners - focuses on basic movement and healing",
        },
        "sample_bot_2": {
            "player_id": "builtin_sample_2",
            "bot_module": "bots.sample_bot2.sample_bot_2",
            "bot_class": "SampleBot2",
            "difficulty": "easy",
            "description": "Another simple bot with slightly different strategy",
        },
        "sample_bot_3": {
            "player_id": "builtin_sample_3",
            "bot_module": "bots.sample_bot3.sample_bot_3",
            "bot_class": "SampleBot3",
            "difficulty": "easy",
            "description": "Third sample bot with basic tactics",
        },
        "tactical_bot": {
            "player_id": "builtin_tactical",
            "bot_module": "bots.tactical_bot.tactical_bot",
            "bot_class": "TacticalBot",
            "difficulty": "medium",
            "description": "An advanced tactical bot with state-based strategy",
        },
        "rincewind_bot": {
            "player_id": "builtin_rincewind",
            "bot_module": "bots.rincewind_bot.rincewind_bot",
            "bot_class": "RincewindBot",
            "difficulty": "medium",
            "description": "A defensive bot that prefers running away and strategic positioning",
        },
        "ai_bot": {
            "player_id": "builtin_ai",
            "bot_module": "bots.ai_bot.ai_bot",
            "bot_class": "AIBot",
            "difficulty": "hard",
            "description": "Deep learning-based bot using DQN for optimal strategies",
        },
    }

    @classmethod
    def get_builtin_player(cls, player_id: str) -> Player:
        """Get built-in player instance."""
        if player_id not in cls.BUILTIN_PLAYERS:
            raise ValueError(f"Built-in player {player_id} not found")
        return cls.BUILTIN_PLAYERS[player_id]

    @classmethod
    def create_bot(cls, bot_id: str) -> BotInterface:
        """Create built-in bot instance with its default player."""
        if bot_id not in cls.BUILTIN_BOTS:
            raise ValueError(f"Built-in bot {bot_id} not found")

        config = cls.BUILTIN_BOTS[bot_id]
        player = cls.get_builtin_player(config["player_id"])

        try:
            # Dynamically import the bot class
            module_name = config["bot_module"]
            class_name = config["bot_class"]

            # Import the module
            import importlib

            module = importlib.import_module(module_name)
            bot_class = getattr(module, class_name)

            # Create wrapped bot instance
            return BuiltinBotWrapper(player, bot_class)

        except ImportError as e:
            logger.error(f"Failed to import bot module {config['bot_module']}: {e}")
            raise ValueError(f"Bot {bot_id} implementation not found")
        except AttributeError as e:
            logger.error(f"Bot class {config['bot_class']} not found in module: {e}")
            raise ValueError(f"Bot {bot_id} class not found")

    @classmethod
    def list_available_bots(cls) -> List[BotInfo]:
        """List all available built-in bots."""
        bots = []
        for bot_id, config in cls.BUILTIN_BOTS.items():
            try:
                player = cls.get_builtin_player(config["player_id"])
                bots.append(
                    BotInfo(
                        bot_type="builtin",
                        bot_id=bot_id,
                        player_id=player.player_id,
                        player_name=player.player_name,
                        description=config.get("description"),
                        difficulty=config.get("difficulty"),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping bot {bot_id} due to error: {e}")
                continue
        return bots

    @classmethod
    def get_all_builtin_players(cls) -> List[Player]:
        """Get all built-in player instances for registration."""
        return list(cls.BUILTIN_PLAYERS.values())

    @classmethod
    def is_builtin_bot(cls, bot_id: str) -> bool:
        """Check if a bot ID corresponds to a built-in bot."""
        return bot_id in cls.BUILTIN_BOTS

    @classmethod
    def is_builtin_player(cls, player_id: str) -> bool:
        """Check if a player ID corresponds to a built-in player."""
        return player_id in cls.BUILTIN_PLAYERS

    @classmethod
    def get_bot_info(cls, bot_id: str) -> BotInfo:
        """Get information about a specific built-in bot."""
        if bot_id not in cls.BUILTIN_BOTS:
            raise ValueError(f"Built-in bot {bot_id} not found")

        config = cls.BUILTIN_BOTS[bot_id]
        player = cls.get_builtin_player(config["player_id"])

        return BotInfo(
            bot_type="builtin",
            bot_id=bot_id,
            player_id=player.player_id,
            player_name=player.player_name,
            description=config.get("description"),
            difficulty=config.get("difficulty"),
        )
