"""TurnProcessor for collecting, validating, and preparing actions per turn (Task 7.2).

Responsibilities:
- Collect actions from players with timeout semantics
- Provide a submission API to store actions as they arrive
- Validate actions against basic constraints (extensible for full rule checks)
- Produce a complete action set for the current turn, filling in defaults for missing

Integration with the game engine (applying actions) is handled in Task 7.3.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..models.actions import ActionData, Move, SpellAction


@dataclass
class _SessionTurnState:
    """Holds pending actions per turn for a specific session."""

    pending_by_turn: Dict[int, Dict[str, Move]] = field(default_factory=dict)


class TurnProcessor:
    """Processes player actions and coordinates per-turn action collection."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds
        self._sessions: Dict[str, _SessionTurnState] = {}
        self._lock = asyncio.Lock()

    async def submit_action(self, session_id: str, player_id: str, turn: int, action: ActionData) -> None:
        """Submit an action for a player for a given turn.

        Stores as a Move for uniform handling during collection.
        """
        move = Move(
            player_id=player_id,
            turn=turn,
            move=action.move,
            spell=SpellAction(**action.spell) if action.spell else None,
        )

        async with self._lock:
            state = self._sessions.setdefault(session_id, _SessionTurnState())
            turn_map = state.pending_by_turn.setdefault(turn, {})
            turn_map[player_id] = move

    async def collect_actions(
        self,
        session_id: str,
        turn: int,
        expected_players: List[str],
        *,
        is_builtin: Optional[Callable[[str], bool]] = None,
    ) -> Dict[str, Move]:
        """Collect actions for all expected players for the given turn.

        - Waits up to timeout for all players to submit
        - Auto-fills built-in players immediately if is_builtin is provided and returns True
        - Fills safe defaults for any missing players on timeout
        """
        async with self._lock:
            state = self._sessions.setdefault(session_id, _SessionTurnState())
            turn_map = state.pending_by_turn.setdefault(turn, {})

        # Auto-fill for built-in players
        if is_builtin is not None:
            for pid in expected_players:
                if is_builtin(pid):
                    async with self._lock:
                        turn_map = state.pending_by_turn.setdefault(turn, {})
                        turn_map.setdefault(pid, Move(player_id=pid, turn=turn, move=None, spell=None))

        # Wait loop
        start = datetime.now()
        while True:
            async with self._lock:
                current = dict(state.pending_by_turn.get(turn, {}))
            if all(pid in current for pid in expected_players):
                break
            elapsed = (datetime.now() - start).total_seconds()
            if elapsed >= self._timeout:
                # Fill defaults
                async with self._lock:
                    missing = [pid for pid in expected_players if pid not in state.pending_by_turn[turn]]
                    for pid in missing:
                        state.pending_by_turn[turn][pid] = Move(player_id=pid, turn=turn, move=[0, 0], spell=None)
                break
            await asyncio.sleep(0.01)

        # Validate collected (basic structure checks)
        async with self._lock:
            collected = dict(state.pending_by_turn.get(turn, {}))
            # Cleanup turn storage after collection to avoid growth
            state.pending_by_turn.pop(turn, None)

        # Basic validation pass (extensible in Task 7.3)
        valid: Dict[str, Move] = {}
        for pid, mv in collected.items():
            if await self.validate_action(mv, {}):
                valid[pid] = mv
            else:
                # Replace invalid with safe default
                valid[pid] = Move(player_id=pid, turn=turn, move=[0, 0], spell=None)

        return valid

    async def validate_action(self, action: Move, game_state: Dict[str, Any]) -> bool:
        """Validate a single action against current game rules (placeholder).

        For Task 7.2 this performs basic schema checks. Full validation is part of Task 7.3.
        """
        # Movement must be None or a 2-int list in range [-1, 1]
        if action.move is not None:
            if not isinstance(action.move, list) or len(action.move) != 2:
                return False
            dx, dy = action.move
            if not isinstance(dx, int) or not isinstance(dy, int):
                return False
            if dx < -1 or dx > 1 or dy < -1 or dy > 1:
                return False

        # Spell payload will be validated later (Task 7.3) — allow any or None for now
        return True

    async def cleanup_session(self, session_id: str) -> None:
        """Cleanup any pending state for a session."""
        async with self._lock:
            self._sessions.pop(session_id, None)
