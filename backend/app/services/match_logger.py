"""Match logging service for the Playground backend (Task 8.1).

Responsibilities:
- Structured, line-based logging of match events to files under logs/playground/
- Minimal in-memory tracking of per-session move history and turn events
- Final summary line on game over
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..core.config import settings
from ..models.actions import Move, MoveHistory
from ..models.events import GameOverEvent, TurnEvent


logger = logging.getLogger(__name__)


def _resolve_log_dir() -> Path:
    """Resolve the playground log directory to an absolute repo-rooted path."""
    # settings.playground_log_dir is a posix-like path relative to repo root by default
    repo_root = Path(__file__).resolve().parents[3]
    log_dir = (repo_root / settings.playground_log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


@dataclass
class _SessionLogState:
    file_path: Path
    moves: MoveHistory = field(default_factory=lambda: MoveHistory(session_id="", moves=[], total_turns=0))
    turn_events: List[TurnEvent] = field(default_factory=list)


class MatchLogger:
    """File-based match logger with simple in-memory tracking."""

    def __init__(self, log_dir: Optional[str] = None) -> None:
        self._base_dir: Path = _resolve_log_dir() if log_dir is None else Path(log_dir).resolve()
        self._sessions: Dict[str, _SessionLogState] = {}

    def _path_for(self, session_id: str) -> Path:
        return self._base_dir / f"{session_id}.log"

    def start_session(self, session_id: str, player_1_name: str, player_2_name: str) -> None:
        """Create/open the log file and write a header line."""
        path = self._path_for(session_id)
        # Initialize state
        state = _SessionLogState(file_path=path)
        state.moves.session_id = session_id
        self._sessions[session_id] = state

        header = f"[{datetime.now().strftime('%H:%M:%S')}] Session start: {player_1_name} vs {player_2_name}\n"
        path.write_text(header, encoding="utf-8")
        logger.info(f"Match log started: {path}")

    def log_turn(self, session_id: str, event: TurnEvent) -> None:
        """Append a single, structured log line for a turn and store event in memory."""
        state = self._sessions.get(session_id)
        if not state:
            # If start_session wasn't called (unexpected), initialize lazily
            # with generic names
            self.start_session(session_id, "Player 1", "Player 2")
            state = self._sessions[session_id]

        # Persist line: one line per turn, include JSON payload for easy parsing
        log_line = f"[{event.timestamp.strftime('%H:%M:%S')}] Turn {event.turn}: {event.log_line} | payload="
        try:
            payload = event.model_dump()
            # Keep log compact: actions/events present already
            log_line += json.dumps(payload, separators=(",", ":"))
        except Exception:
            log_line += "{}"
        with state.file_path.open("a", encoding="utf-8") as fp:
            fp.write(log_line + "\n")

        # Track in-memory event list for potential diagnostics
        state.turn_events.append(event)

    def log_game_over(self, session_id: str, event: GameOverEvent) -> None:
        """Write a final summary line and flush state."""
        state = self._sessions.get(session_id)
        if not state:
            # Nothing to do
            return
        summary = (
            f"[{event.timestamp.strftime('%H:%M:%S')}] Game over: winner={event.winner or 'draw'}"
        )
        with state.file_path.open("a", encoding="utf-8") as fp:
            fp.write(summary + "\n")

    def get_log_path(self, session_id: str) -> Path:
        return self._path_for(session_id)

    def get_turn_events(self, session_id: str) -> List[TurnEvent]:
        state = self._sessions.get(session_id)
        if not state:
            return []
        return list(state.turn_events)

    def finalize(self, session_id: str) -> None:
        """Cleanup in-memory state; leaves file on disk."""
        self._sessions.pop(session_id, None)

