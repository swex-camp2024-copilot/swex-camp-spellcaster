"""Player registry service for managing all players in the Spellcasters Playground Backend."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..core.exceptions import PlayerNotFoundError, PlayerRegistrationError
from ..models.players import Player, PlayerRegistration
from ..models.results import GameResult
from .database import DatabaseService

logger = logging.getLogger(__name__)


class PlayerRegistry:
    """Manages all players (both user-registered and built-in) with database persistence."""

    def __init__(self, db_service: DatabaseService):
        """Initialize the player registry with database service."""
        self.db = db_service
        self._builtin_players_cache: Dict[str, Player] = {}

    async def initialize(self) -> None:
        """Initialize the registry by ensuring database tables exist and registering built-in players."""
        await self.db.ensure_tables_exist()
        await self._register_builtin_players()
        logger.info("PlayerRegistry initialized with built-in players")

    async def _register_builtin_players(self) -> None:
        """Register all built-in players at startup."""
        builtin_players = self._get_builtin_player_definitions()

        for player in builtin_players:
            try:
                await self.db.create_builtin_player(player)
                self._builtin_players_cache[player.player_id] = player
                logger.debug(f"Registered built-in player: {player.player_name}")
            except Exception as e:
                logger.error(f"Failed to register built-in player {player.player_name}: {e}")
                # Continue with other players even if one fails

    def _get_builtin_player_definitions(self) -> List[Player]:
        """Get hard-coded built-in player definitions from the BuiltinBotRegistry."""
        from .builtin_bots import BuiltinBotRegistry
        return BuiltinBotRegistry.get_all_builtin_players()

    # Player Management Operations

    async def register_player(self, registration: PlayerRegistration) -> Player:
        """Register a new user player with database persistence."""
        try:
            # Validate registration data
            if not registration.player_name or registration.player_name.strip() == "":
                raise PlayerRegistrationError("Player name cannot be empty")

            # Check for duplicate names (optional business rule)
            existing_players = await self.db.list_all_players(include_builtin=True)
            for existing in existing_players:
                if existing.player_name.lower() == registration.player_name.lower():
                    logger.warning(f"Player name '{registration.player_name}' already exists")
                    # Allow duplicate names for now, but log for monitoring

            # Create player in database
            player = await self.db.create_player(registration)
            logger.info(f"Registered new player: {player.player_id} ({player.player_name})")
            return player

        except Exception as e:
            logger.error(f"Failed to register player '{registration.player_name}': {e}")
            if isinstance(e, PlayerRegistrationError):
                raise
            raise PlayerRegistrationError(f"Registration failed: {str(e)}")

    async def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID from database or built-in cache."""
        try:
            # First check database (covers both user and built-in players)
            player = await self.db.get_player(player_id)
            if player:
                return player

            # Fallback to built-in cache if not found in database
            if player_id in self._builtin_players_cache:
                return self._builtin_players_cache[player_id]

            return None

        except Exception as e:
            logger.error(f"Error retrieving player {player_id}: {e}")
            return None

    async def get_player_or_raise(self, player_id: str) -> Player:
        """Get player by ID or raise PlayerNotFoundError if not found."""
        player = await self.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)
        return player

    async def update_player_stats(self, player_id: str, result: GameResult) -> None:
        """Update player statistics after a match."""
        try:
            await self.db.update_player_stats(player_id, result)
            logger.info(f"Updated stats for player {player_id}")

        except Exception as e:
            logger.error(f"Failed to update stats for player {player_id}: {e}")
            raise

    async def list_players(self, include_builtin: bool = True) -> List[Player]:
        """List all players with optional filtering."""
        try:
            players = await self.db.list_all_players(include_builtin=include_builtin)
            return players

        except Exception as e:
            logger.error(f"Error listing players: {e}")
            return []

    async def list_builtin_players(self) -> List[Player]:
        """List only built-in players."""
        try:
            all_players = await self.db.list_all_players(include_builtin=True)
            return [p for p in all_players if p.is_builtin]

        except Exception as e:
            logger.error(f"Error listing built-in players: {e}")
            return list(self._builtin_players_cache.values())

    async def list_user_players(self) -> List[Player]:
        """List only user-registered players."""
        return await self.list_players(include_builtin=False)

    async def get_player_count(self, include_builtin: bool = True) -> int:
        """Get total number of players."""
        try:
            players = await self.list_players(include_builtin=include_builtin)
            return len(players)

        except Exception as e:
            logger.error(f"Error getting player count: {e}")
            return 0

    # Built-in Player Management

    def get_builtin_player_ids(self) -> List[str]:
        """Get list of all built-in player IDs."""
        return list(self._builtin_players_cache.keys())

    async def is_builtin_player(self, player_id: str) -> bool:
        """Check if a player ID corresponds to a built-in player."""
        player = await self.get_player(player_id)
        return player.is_builtin if player else False

    # Utility Methods

    async def validate_player_exists(self, player_id: str) -> bool:
        """Validate that a player exists."""
        player = await self.get_player(player_id)
        return player is not None

    async def get_player_statistics_summary(self) -> Dict[str, int]:
        """Get summary statistics about players."""
        try:
            total_players = await self.get_player_count(include_builtin=True)
            user_players = await self.get_player_count(include_builtin=False)
            builtin_players = len(self._builtin_players_cache)

            return {
                "total_players": total_players,
                "user_players": user_players,
                "builtin_players": builtin_players,
            }

        except Exception as e:
            logger.error(f"Error getting player statistics: {e}")
            return {"total_players": 0, "user_players": 0, "builtin_players": 0}

    async def delete_player(self, player_id: str) -> bool:
        """Delete a player with validation and constraint checking."""
        try:
            # Validate player exists and get details
            player = await self.get_player(player_id)
            if not player:
                raise PlayerNotFoundError(player_id)

            # Prevent deletion of built-in players
            if player.is_builtin:
                raise PlayerRegistrationError("Cannot delete built-in players")

            # Delegate to database service for actual deletion
            success = await self.db.delete_player(player_id)
            
            if success:
                # Remove from built-in cache if it was there (shouldn't happen, but safety)
                if player_id in self._builtin_players_cache:
                    del self._builtin_players_cache[player_id]
                
                logger.info(f"Successfully deleted player: {player_id} ({player.player_name})")
                return True
            
            return False

        except (PlayerNotFoundError, PlayerRegistrationError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete player {player_id}: {e}")
            raise PlayerRegistrationError(f"Player deletion failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup resources (if needed)."""
        logger.info("PlayerRegistry cleanup completed") 