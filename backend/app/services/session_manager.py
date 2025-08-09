"""Session management and game flow coordination for the Playground backend."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import SessionNotFoundError
from ..models.bots import BotInterface, BotCreationRequest, PlayerBotFactory
from ..models.events import GameOverEvent, TurnEvent
from ..models.players import PlayerConfig
from ..models.sessions import GameState, PlayerSlot, TurnStatus
from .builtin_bots import BuiltinBotRegistry
from .database import DatabaseService
from .game_adapter import GameEngineAdapter

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    session_id: str
    game_state: GameState
    adapter: GameEngineAdapter
    task: Optional[asyncio.Task]
    created_at: datetime


class SessionManager:
    """Creates and manages game sessions and the match loop."""

    def __init__(self, db_service: Optional[DatabaseService] = None):
        self._db = db_service or DatabaseService()
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, player_1: PlayerConfig, player_2: PlayerConfig) -> str:
        """Create a new session and start the match loop.

        Returns the new session_id.
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

        # Start match loop
        context.task = asyncio.create_task(self._run_match_loop(context))
        logger.info(f"Session {session_id} created: {bot1.name} vs {bot2.name}")
        return session_id

    async def _create_bot_from_config(self, cfg: PlayerConfig) -> BotInterface:
        if cfg.bot_type == "builtin":
            if not cfg.bot_id:
                raise ValueError("bot_id required for builtin bot")
            return BuiltinBotRegistry.create_bot(cfg.bot_id)

        # Player-submitted bot: for now create a do-nothing stub that holds player identity
        # In a later task, this will tie into real client-submitted code or SSE
        dummy_code = "def decide(state):\n    return {\"move\": [0, 0], \"spell\": None}"
        request = BotCreationRequest(bot_code=dummy_code, player_id=cfg.player_id)
        return PlayerBotFactory.create_bot(request, player_registry=MockRegistry(self._db))

    async def _run_match_loop(self, ctx: SessionContext) -> None:
        """Run the automated match loop until completion."""
        try:
            start_time = datetime.now()
            while True:
                # Execute a single turn
                turn_event: TurnEvent = await ctx.adapter.execute_turn()  # type: ignore[assignment]

                # Update in-memory state
                ctx.game_state.turn_index = turn_event.turn
                ctx.game_state.current_game_state = turn_event.game_state
                ctx.game_state.add_log_entry(turn_event.log_line)

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

                    logger.info(
                        f"Session {ctx.session_id} completed in {result.total_rounds} rounds. Winner: {result.winner}"
                    )
                    break

                # Small scheduling yield to avoid blocking event loop
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info(f"Session {ctx.session_id} cancelled")
            ctx.game_state.status = TurnStatus.CANCELLED
            raise
        except Exception as e:
            logger.error(f"Error in session {ctx.session_id} loop: {e}", exc_info=True)
            ctx.game_state.status = TurnStatus.CANCELLED

    async def get_session(self, session_id: str) -> SessionContext:
        async with self._lock:
            ctx = self._sessions.get(session_id)
        if not ctx:
            raise SessionNotFoundError(session_id)
        return ctx

    async def list_active_sessions(self) -> List[str]:
        async with self._lock:
            return [s for s, c in self._sessions.items() if c.game_state.status == TurnStatus.ACTIVE]

    async def cleanup_session(self, session_id: str) -> bool:
        async with self._lock:
            ctx = self._sessions.get(session_id)
        if not ctx:
            raise SessionNotFoundError(session_id)
        if ctx.task and not ctx.task.done():
            ctx.task.cancel()
            try:
                await ctx.task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            self._sessions.pop(session_id, None)
        return True


class MockRegistry:
    """Minimal adapter to reuse PlayerRegistry API shape for factory without full service."""

    def __init__(self, db: DatabaseService):
        self._db = db

    def get_player(self, player_id: str):  # sync wrapper calling async not needed here, using db directly
        # In this simplified MVP, assume player exists. Real implementation will have proper registry.
        # This layer is kept to satisfy PlayerBotFactory interface.
        # For now, we return None to force factory to require registration pathway in future tasks.
        return None

