"""Session management and game flow coordination for the Playground backend."""

import asyncio
import contextlib
import logging
import multiprocessing
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from ..core.exceptions import SessionNotFoundError
from ..models.actions import ActionData
from ..models.bots import BotInterface, HumanBot, PlayerBot
from ..models.players import PlayerConfig
from ..models.sessions import GameState, PlayerSlot, TurnStatus
from .builtin_bots import BuiltinBotRegistry
from .database import DatabaseService
from .game_adapter import GameEngineAdapter
from .match_logger import MatchLogger
from .sse_manager import SSEManager
from .turn_processor import TurnProcessor
from .visualizer_service import VisualizerService

if TYPE_CHECKING:
    from ..models.events import TurnEvent

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    session_id: str
    game_state: GameState
    adapter: GameEngineAdapter
    task: Optional[asyncio.Task]
    created_at: datetime

    # Visualization support
    visualizer_process: Optional[multiprocessing.Process] = None
    visualizer_queue: Optional[multiprocessing.Queue] = None
    visualizer_enabled: bool = False


class SessionManager:
    """Creates and manages game sessions and the match loop."""

    def __init__(
        self,
        db_service: Optional[DatabaseService] = None,
        sse_manager: Optional[SSEManager] = None,
        match_logger: Optional[MatchLogger] = None,
        visualizer_service: Optional[VisualizerService] = None,
    ):
        self._db = db_service or DatabaseService()
        self._sse = sse_manager
        self._sessions: dict[str, SessionContext] = {}
        self._turn_processor = TurnProcessor()
        self._lock = asyncio.Lock()
        self._logger = match_logger
        self._visualizer_service = visualizer_service or VisualizerService()

    async def create_session(self, player_1: PlayerConfig, player_2: PlayerConfig, visualize: bool = False) -> str:
        """Create a new session and start the match loop.

        Args:
            player_1: Configuration for player 1
            player_2: Configuration for player 2
            visualize: Whether to spawn a visualizer process for this session

        Returns:
            The new session_id.
        """
        session_id = str(uuid4())

        # Build bot instances from configs
        bot1 = await self._create_bot_from_config(player_1)
        bot2 = await self._create_bot_from_config(player_2)

        # Initialize game state
        game_state = GameState(
            session_id=session_id,
            player_1=PlayerSlot(
                player_id=bot1.player_id,
                player_name=bot1.name,
                is_builtin_bot=bot1.is_builtin,
            ),
            player_2=PlayerSlot(
                player_id=bot2.player_id,
                player_name=bot2.name,
                is_builtin_bot=bot2.is_builtin,
            ),
            status=TurnStatus.ACTIVE,
        )

        # Persist session record
        await self._db.create_session_record(session_id, bot1.player_id, bot2.player_id)

        # Initialize engine adapter
        adapter = GameEngineAdapter()
        adapter.initialize_match(bot1, bot2)

        # Save context
        context = SessionContext(
            session_id=session_id,
            game_state=game_state,
            adapter=adapter,
            task=None,
            created_at=datetime.now(),
        )
        async with self._lock:
            self._sessions[session_id] = context

        # Spawn visualizer if requested
        if visualize:
            try:
                process, queue = self._visualizer_service.spawn_visualizer(
                    session_id=session_id,
                    player1_name=bot1.name,
                    player2_name=bot2.name,
                    player1_sprite=getattr(bot1, "wizard_sprite_path", None),
                    player2_sprite=getattr(bot2, "wizard_sprite_path", None),
                )
                if process and queue:
                    context.visualizer_process = process
                    context.visualizer_queue = queue
                    context.visualizer_enabled = True
                    logger.info(f"Visualizer spawned for session {session_id} (PID: {process.pid})")
                else:
                    logger.warning(f"Failed to spawn visualizer for session {session_id}, continuing headless")
            except Exception as exc:
                logger.error(f"Error spawning visualizer for session {session_id}: {exc}", exc_info=True)

        # Start match loop
        context.task = asyncio.create_task(self._run_match_loop(context))
        logger.info(f"Session {session_id} created: {bot1.name} vs {bot2.name}")
        # Initialize match logging
        try:
            if self._logger:
                self._logger.start_session(session_id, bot1.name, bot2.name)
        except Exception as exc:
            logger.warning(f"Failed to start match log for {session_id}: {exc}")
        return session_id

    async def _create_bot_from_config(self, cfg: PlayerConfig) -> BotInterface:
        if cfg.bot_type == "builtin":
            if not cfg.bot_id:
                raise ValueError("bot_id required for builtin bot")
            return BuiltinBotRegistry.create_bot(cfg.bot_id)

        # Player-submitted bot: create a stub PlayerBot bound to existing player
        if not cfg.player_id:
            raise ValueError("player_id required for player bot")
        player = await self._db.get_player(cfg.player_id)
        if not player:
            raise ValueError(f"Player {cfg.player_id} not found")
        dummy_code = 'def decide(state):\n    return {"move": [0, 0], "spell": None}'
        return PlayerBot(player, dummy_code)

    async def _run_match_loop(self, ctx: SessionContext) -> None:
        """Run the automated match loop until completion."""
        try:
            start_time = datetime.now()
            # Small delay to allow SSE clients to connect before game starts
            await asyncio.sleep(0.1)
            while True:
                expected_players = [ctx.game_state.player_1.player_id, ctx.game_state.player_2.player_id]
                next_turn = ctx.game_state.turn_index + 1

                # Collect actions with timeout semantics via TurnProcessor.
                def _is_builtin(pid: str) -> bool:
                    return (pid == ctx.game_state.player_1.player_id and ctx.game_state.player_1.is_builtin_bot) or (
                        pid == ctx.game_state.player_2.player_id and ctx.game_state.player_2.is_builtin_bot
                    )

                collected_actions = await self._turn_processor.collect_actions(
                    ctx.session_id, next_turn, expected_players, is_builtin=_is_builtin
                )

                # Execute a single turn on the engine
                turn_event: TurnEvent = await ctx.adapter.execute_turn()  # type: ignore[assignment]

                # Update in-memory state
                ctx.game_state.turn_index = turn_event.turn
                ctx.game_state.current_game_state = turn_event.game_state
                # Override/attach collected action summaries for observability
                turn_event.actions = [
                    {
                        "player_id": move.player_id,
                        "turn": move.turn,
                        "move": move.move,
                        "spell": (move.spell.model_dump() if move.spell else None),
                    }
                    for move in collected_actions.values()
                ]
                ctx.game_state.add_log_entry(turn_event.log_line)

                # Broadcast turn update over SSE if configured
                if self._sse:
                    await self._sse.broadcast(ctx.session_id, turn_event)

                # Send to visualizer if enabled
                if ctx.visualizer_enabled and ctx.visualizer_queue:
                    try:
                        self._visualizer_service.send_event(ctx.visualizer_queue, turn_event)
                    except Exception as exc:
                        logger.warning(f"Failed to send turn event to visualizer for {ctx.session_id}: {exc}")

                # Log turn to file
                if self._logger:
                    try:
                        self._logger.log_turn(ctx.session_id, turn_event)
                    except Exception as exc:
                        logger.warning(f"Failed to log turn for {ctx.session_id}: {exc}")

                # Small delay between turns to allow SSE event delivery
                await asyncio.sleep(0.01)

                # Check game over
                result = ctx.adapter.check_game_over()
                if result is not None:
                    # Finalize result metadata
                    result.session_id = ctx.session_id
                    result.game_duration = (datetime.now() - start_time).total_seconds()

                    # Persist completion
                    await self._db.complete_session(ctx.session_id, result)

                    # Mark status and store winner
                    ctx.game_state.status = TurnStatus.COMPLETED
                    ctx.game_state.winner_id = result.winner

                    # Broadcast game over event
                    game_over_event = ctx.adapter.create_game_over_event(result)
                    if self._sse:
                        await self._sse.broadcast(ctx.session_id, game_over_event)
                        # Close all SSE streams for this session
                        await self._sse.close_session_streams(ctx.session_id)

                    # Send to visualizer if enabled
                    if ctx.visualizer_enabled and ctx.visualizer_queue:
                        try:
                            self._visualizer_service.send_event(ctx.visualizer_queue, game_over_event)
                        except Exception as exc:
                            logger.warning(f"Failed to send game over event to visualizer for {ctx.session_id}: {exc}")

                    # Log game over
                    if self._logger:
                        try:
                            self._logger.log_game_over(ctx.session_id, game_over_event)
                        except Exception as exc:
                            logger.warning(f"Failed to write game over log for {ctx.session_id}: {exc}")

                    logger.info(
                        f"Session {ctx.session_id} completed in {result.total_rounds} rounds. Winner: {result.winner}"
                    )
                    break

                # Small scheduling yield to avoid blocking event loop
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info(f"Session {ctx.session_id} cancelled")
            ctx.game_state.status = TurnStatus.CANCELLED
            # Close SSE streams on cancellation
            if self._sse:
                await self._sse.close_session_streams(ctx.session_id)
            raise
        except Exception as e:
            logger.error(f"Error in session {ctx.session_id} loop: {e}", exc_info=True)
            ctx.game_state.status = TurnStatus.CANCELLED
            # Close SSE streams on error
            if self._sse:
                await self._sse.close_session_streams(ctx.session_id)
        finally:
            # NOTE: Visualizer is NOT terminated automatically when session ends.
            # It remains open to show the final game state.
            # Admin can manually terminate via cleanup_session() API or user can close the window.
            pass

    async def get_session(self, session_id: str) -> SessionContext:
        async with self._lock:
            ctx = self._sessions.get(session_id)
        if not ctx:
            raise SessionNotFoundError(session_id)
        return ctx

    async def list_active_sessions(self) -> list[str]:
        async with self._lock:
            return [s for s, c in self._sessions.items() if c.game_state.status == TurnStatus.ACTIVE]

    async def cleanup_session(self, session_id: str) -> bool:
        async with self._lock:
            ctx = self._sessions.get(session_id)
        if not ctx:
            raise SessionNotFoundError(session_id)

        # Terminate visualizer before cancelling task
        if ctx.visualizer_enabled and ctx.visualizer_process:
            try:
                logger.info(f"Terminating visualizer for session {session_id} during cleanup")
                self._visualizer_service.terminate_visualizer(ctx.visualizer_process, ctx.visualizer_queue)
            except Exception as exc:
                logger.error(f"Error terminating visualizer during cleanup for {session_id}: {exc}", exc_info=True)

        if ctx.task and not ctx.task.done():
            ctx.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ctx.task
        async with self._lock:
            self._sessions.pop(session_id, None)
        return True

    async def submit_action(self, session_id: str, player_id: str, turn: int, action: ActionData) -> None:
        """Submit an action and also set on HumanBot if applicable."""
        # Store via turn processor
        await self._turn_processor.submit_action(session_id, player_id, turn, action)

        # Also set on HumanBot if the player's bot is human-controlled
        async with self._lock:
            ctx = self._sessions.get(session_id)
        if not ctx:
            return
        bot_map: dict[str, BotInterface] = {
            ctx.adapter.bot1.player_id
            if hasattr(ctx.adapter, "bot1")
            else ctx.game_state.player_1.player_id: ctx.adapter.bot1 if hasattr(ctx.adapter, "bot1") else None,
            ctx.adapter.bot2.player_id
            if hasattr(ctx.adapter, "bot2")
            else ctx.game_state.player_2.player_id: ctx.adapter.bot2 if hasattr(ctx.adapter, "bot2") else None,
        }
        bot = bot_map.get(player_id)
        if isinstance(bot, HumanBot):
            bot.set_action(action)

    # Removed old _collect_actions in favor of TurnProcessor


class MockRegistry:
    """Minimal adapter to reuse PlayerRegistry API shape for factory without full service."""

    def __init__(self, db: DatabaseService):
        self._db = db

    def get_player(self, player_id: str):  # sync wrapper calling async not needed here, using db directly
        # In this simplified MVP, assume player exists. Real implementation will have proper registry.
        # This layer is kept to satisfy PlayerBotFactory interface.
        # For now, we return None to force factory to require registration pathway in future tasks.
        return None
