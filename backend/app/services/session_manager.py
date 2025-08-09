"""Session management and game flow coordination for the Playground backend."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import SessionNotFoundError
from ..models.actions import ActionData, Move, SpellAction
from ..models.bots import BotInterface, BotCreationRequest, PlayerBotFactory, PlayerBot
from ..models.events import GameOverEvent, TurnEvent
from ..models.players import PlayerConfig
from ..models.sessions import GameState, PlayerSlot, TurnStatus
from .builtin_bots import BuiltinBotRegistry
from .sse_manager import SSEManager
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

    def __init__(self, db_service: Optional[DatabaseService] = None, sse_manager: Optional[SSEManager] = None):
        self._db = db_service or DatabaseService()
        self._sse = sse_manager
        self._sessions: Dict[str, SessionContext] = {}
        # Pending actions per session_id -> turn_index -> {player_id: Move}
        self._pending_actions: Dict[str, Dict[int, Dict[str, Move]]] = {}
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

        # Player-submitted bot: create a stub PlayerBot bound to existing player
        if not cfg.player_id:
            raise ValueError("player_id required for player bot")
        player = await self._db.get_player(cfg.player_id)
        if not player:
            raise ValueError(f"Player {cfg.player_id} not found")
        dummy_code = "def decide(state):\n    return {\"move\": [0, 0], \"spell\": None}"
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

                # Collect actions with timeout semantics. Built-in bots are auto-collected.
                collected_actions = await self._collect_actions(ctx, next_turn, expected_players)

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
                    if self._sse:
                        await self._sse.broadcast(ctx.session_id, ctx.adapter.create_game_over_event(result))
                        # Close all SSE streams for this session
                        await self._sse.close_session_streams(ctx.session_id)

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

    async def submit_action(self, session_id: str, player_id: str, turn: int, action: ActionData) -> None:
        """Submit an action for a player for a given turn (for future API integration)."""
        async with self._lock:
            by_turn = self._pending_actions.setdefault(session_id, {})
            turn_map = by_turn.setdefault(turn, {})
            # Store as Move for uniform handling
            turn_map[player_id] = Move(player_id=player_id, turn=turn, move=action.move, spell=(SpellAction(**action.spell) if action.spell else None))

    async def _collect_actions(
        self, ctx: SessionContext, turn: int, expected_players: List[str]
    ) -> Dict[str, Move]:
        """Collect actions from players with timeout semantics. Built-in bots are auto-decided."""
        timeout_seconds = 5.0

        # Initialize collection from any pending submissions
        async with self._lock:
            by_turn = self._pending_actions.setdefault(ctx.session_id, {})
            turn_map = by_turn.setdefault(turn, {})

        # Auto-fill for built-in bots to avoid waiting
        builtin_ids = {
            ctx.game_state.player_1.player_id: ctx.game_state.player_1.is_builtin_bot,
            ctx.game_state.player_2.player_id: ctx.game_state.player_2.is_builtin_bot,
        }
        for pid in expected_players:
            if builtin_ids.get(pid) and pid not in turn_map:
                # Auto-collect placeholder; engine will compute actual action
                turn_map[pid] = Move(player_id=pid, turn=turn, move=None, spell=None)

        # Wait until all expected players present or timeout
        start = datetime.now()
        while True:
            if all(pid in turn_map for pid in expected_players):
                break
            elapsed = (datetime.now() - start).total_seconds()
            if elapsed >= timeout_seconds:
                # Fill missing with safe default action
                for pid in expected_players:
                    if pid not in turn_map:
                        turn_map[pid] = Move(player_id=pid, turn=turn, move=[0, 0], spell=None)
                break
            await asyncio.sleep(0.01)

        # Copy out and clear stored actions for this turn to avoid growth
        async with self._lock:
            collected = dict(turn_map)
            # Optionally keep history; for now, release memory for the turn
            by_turn.pop(turn, None)
        return collected


class MockRegistry:
    """Minimal adapter to reuse PlayerRegistry API shape for factory without full service."""

    def __init__(self, db: DatabaseService):
        self._db = db

    def get_player(self, player_id: str):  # sync wrapper calling async not needed here, using db directly
        # In this simplified MVP, assume player exists. Real implementation will have proper registry.
        # This layer is kept to satisfy PlayerBotFactory interface.
        # For now, we return None to force factory to require registration pathway in future tasks.
        return None

