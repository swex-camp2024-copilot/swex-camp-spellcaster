"""Game engine adapter for the Spellcasters Playground Backend."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..models.bots import BotInterface
from ..models.actions import Move, MoveResult, SpellAction
from ..models.results import GameResult, GameResultType, PlayerGameStats
from ..models.events import TurnEvent, GameOverEvent

logger = logging.getLogger(__name__)

# Expose a module-level GameEngine reference for tests to patch.
# It will be lazily imported on first use if not patched.
GameEngine = None  # type: ignore[assignment]


class GameEngineAdapter:
    """
    Adapter between backend and existing game engine.
    Bridges the gap between the new bot interface and existing game engine.
    """

    def __init__(self):
        """Initialize the game engine adapter."""
        self.engine = None
        self.bot1 = None
        self.bot2 = None
        self._turn_events = []
        self._game_started = False

    def initialize_match(self, bot1: BotInterface, bot2: BotInterface) -> None:
        """
        Initialize game engine with bot instances.
        
        Args:
            bot1: First bot instance
            bot2: Second bot instance
        """
        try:
            # Ensure GameEngine is available (allowing tests to patch this symbol)
            global GameEngine
            if GameEngine is None:
                from game.engine import GameEngine as _GameEngine
                GameEngine = _GameEngine

            self.bot1 = bot1
            self.bot2 = bot2
            
            # Create the game engine with bot instances
            self.engine = GameEngine(bot1, bot2)
            self._game_started = True
            self._turn_events = []
            
            logger.info(f"Game initialized: {bot1.name} vs {bot2.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize game engine: {e}")
            raise RuntimeError(f"Game initialization failed: {e}")

    async def execute_turn(self) -> Optional[TurnEvent]:
        """
        Execute a single turn and return turn events.
        
        Returns:
            TurnEvent with turn results, or None if game ended
        """
        if not self.engine or not self._game_started:
            raise RuntimeError("Game engine not initialized")

        try:
            # Store current turn number before execution
            current_turn = self.engine.turn
            
            # Execute the turn using the existing game engine
            self.engine.run_turn()
            
            # Get the current game state after turn execution
            game_state = self.get_game_state()
            
            # Extract turn events from the game logger
            events = self._extract_turn_events()
            
            # Create turn event
            turn_event = TurnEvent(
                turn=current_turn + 1,  # Turn number after execution
                game_state=game_state,
                actions=self._extract_move_results(),
                events=events,
                log_line=self._format_log_line(current_turn + 1, events)
            )
            
            self._turn_events.append(turn_event)
            return turn_event
            
        except Exception as e:
            logger.error(f"Error executing turn: {e}")
            raise RuntimeError(f"Turn execution failed: {e}")

    def get_game_state(self) -> Dict[str, Any]:
        """
        Get current game state for SSE streaming.
        
        Returns:
            Dictionary containing current game state
        """
        if not self.engine:
            return {}

        try:
            # Use the existing build_input method to get state
            state = self.engine.build_input(self.engine.wizard1, self.engine.wizard2)
            
            # Add additional backend-specific information
            state.update({
                "session_info": {
                    "turn": self.engine.turn,
                    "player_1": {
                        "player_id": self.bot1.player_id,
                        "name": self.bot1.name,
                        "hp": self.engine.wizard1.hp,
                        "mana": self.engine.wizard1.mana,
                        "position": self.engine.wizard1.position,
                        "is_alive": self.engine.wizard1.hp > 0
                    },
                    "player_2": {
                        "player_id": self.bot2.player_id,
                        "name": self.bot2.name,
                        "hp": self.engine.wizard2.hp,
                        "mana": self.engine.wizard2.mana,
                        "position": self.engine.wizard2.position,
                        "is_alive": self.engine.wizard2.hp > 0
                    }
                }
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Error getting game state: {e}")
            return {}

    def check_game_over(self) -> Optional[GameResult]:
        """
        Check if game has ended and return result.
        
        Returns:
            GameResult if game ended, None if still ongoing
        """
        if not self.engine:
            return None

        try:
            winner = self.engine.check_winner()
            
            if winner is None:
                # Check for maximum turns (100 turns limit)
                if self.engine.turn >= 100:
                    return self._create_game_result("max_turns", None)
                return None
            
            # Game is over
            if winner == "Draw":
                return self._create_game_result("draw", None)
            elif winner == self.bot1:
                return self._create_game_result("hp_zero", self.bot1.player_id)
            elif winner == self.bot2:
                return self._create_game_result("hp_zero", self.bot2.player_id)
            else:
                logger.warning(f"Unknown winner type: {winner}")
                return self._create_game_result("unknown", None)
                
        except Exception as e:
            logger.error(f"Error checking game over: {e}")
            return None

    def get_turn_events(self) -> List[TurnEvent]:
        """Get all turn events from the current game."""
        return self._turn_events.copy()

    def create_game_over_event(self, game_result: GameResult) -> GameOverEvent:
        """
        Create a game over event from the game result.
        
        Args:
            game_result: The final game result
            
        Returns:
            GameOverEvent for SSE streaming
        """
        return GameOverEvent(
            winner=game_result.winner,
            final_state=self.get_game_state(),
            game_result=game_result
        )

    def _create_game_result(self, end_condition: str, winner_id: Optional[str]) -> GameResult:
        """Create a GameResult from the current game state."""
        try:
            # Determine result type and participants
            if end_condition == "draw" or winner_id is None:
                result_type = GameResultType.DRAW
                winner = None
                loser = None
            elif winner_id == self.bot1.player_id:
                result_type = GameResultType.WIN
                winner = self.bot1.player_id
                loser = self.bot2.player_id
            else:
                result_type = GameResultType.WIN
                winner = self.bot2.player_id
                loser = self.bot1.player_id

            # Calculate player stats
            player1_stats = PlayerGameStats(
                player_id=self.bot1.player_id,
                final_hp=self.engine.wizard1.hp,
                final_mana=self.engine.wizard1.mana,
                final_position=self.engine.wizard1.position,
                damage_dealt=self._calculate_damage_dealt(self.bot1.player_id),
                damage_received=self._calculate_damage_received(self.bot1.player_id),
                spells_cast=self._calculate_spells_cast(self.bot1.player_id),
                artifacts_collected=self._calculate_artifacts_collected(self.bot1.player_id)
            )

            player2_stats = PlayerGameStats(
                player_id=self.bot2.player_id,
                final_hp=self.engine.wizard2.hp,
                final_mana=self.engine.wizard2.mana,
                final_position=self.engine.wizard2.position,
                damage_dealt=self._calculate_damage_dealt(self.bot2.player_id),
                damage_received=self._calculate_damage_received(self.bot2.player_id),
                spells_cast=self._calculate_spells_cast(self.bot2.player_id),
                artifacts_collected=self._calculate_artifacts_collected(self.bot2.player_id)
            )

            # Create the game result
            from datetime import datetime
            
            return GameResult(
                session_id="",  # Will be set by session manager
                winner=winner,
                loser=loser,
                result_type=result_type,
                total_rounds=self.engine.turn,
                first_player=self.bot1.player_id,  # Bot1 always starts first
                game_duration=0.0,  # Will be calculated by session manager
                final_scores={
                    self.bot1.player_id: player1_stats,
                    self.bot2.player_id: player2_stats
                },
                end_condition=end_condition,
                created_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error creating game result: {e}")
            # Return a basic result in case of error
            from datetime import datetime
            return GameResult(
                session_id="",
                winner=None,
                loser=None,
                result_type=GameResultType.DRAW,
                total_rounds=self.engine.turn if self.engine else 0,
                first_player=self.bot1.player_id if self.bot1 else "",
                game_duration=0.0,
                final_scores={},
                end_condition="error",
                created_at=datetime.now()
            )

    def _extract_turn_events(self) -> List[str]:
        """Extract events from the game logger for the current turn."""
        try:
            if not self.engine or not hasattr(self.engine, 'logger'):
                return []
            
            # Get the current turn logs from the game logger
            if hasattr(self.engine.logger, 'current_turn'):
                return self.engine.logger.current_turn.copy()
            
            return []
            
        except Exception as e:
            logger.error(f"Error extracting turn events: {e}")
            return []

    def _extract_move_results(self) -> List[MoveResult]:
        """Extract move results from the current turn."""
        # This is a simplified implementation
        # In a full implementation, you would extract detailed move results
        # from the game engine's logger or state
        try:
            results = []
            
            # Create basic move results for both players
            if self.engine:
                results.append(MoveResult(
                    success=True,
                    damage_dealt=0,  # Would be calculated from game events
                    damage_received=0,  # Would be calculated from game events
                    position_after=self.engine.wizard1.position,
                    events=["Move executed"]  # Would be extracted from game logger
                ))
                
                results.append(MoveResult(
                    success=True,
                    damage_dealt=0,
                    damage_received=0,
                    position_after=self.engine.wizard2.position,
                    events=["Move executed"]
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting move results: {e}")
            return []

    def _format_log_line(self, turn: int, events: List[str]) -> str:
        """Format a single log line for the turn."""
        if not events:
            return f"Turn {turn}: No events"
        
        # Join the most important events into a single line
        event_summary = "; ".join(events[:3])  # Take first 3 events
        return f"Turn {turn}: {event_summary}"

    def _calculate_damage_dealt(self, player_id: str) -> int:
        """Calculate total damage dealt by a player."""
        # This would be implemented by analyzing game logger events
        # For now, return 0 as placeholder
        return 0

    def _calculate_damage_received(self, player_id: str) -> int:
        """Calculate total damage received by a player."""
        # This would be implemented by analyzing game logger events
        # For now, return 0 as placeholder
        return 0

    def _calculate_spells_cast(self, player_id: str) -> int:
        """Calculate total spells cast by a player."""
        # This would be implemented by analyzing game logger events
        # For now, return 0 as placeholder
        return 0

    def _calculate_artifacts_collected(self, player_id: str) -> int:
        """Calculate total artifacts collected by a player."""
        # This would be implemented by analyzing game logger events
        # For now, return 0 as placeholder
        return 0