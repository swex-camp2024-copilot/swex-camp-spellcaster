"""Administrative operations service (Task 9.1)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

from ..models.players import Player
from ..models.sessions import TurnStatus
from .database import DatabaseService
from .session_manager import SessionManager


logger = logging.getLogger(__name__)


@dataclass
class AdminPlayerInfo:
    player_id: str
    player_name: str
    submitted_from: str
    total_matches: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    created_at: datetime
    is_builtin: bool


@dataclass
class AdminSessionInfo:
    session_id: str
    player_1_name: str
    player_2_name: str
    status: str
    turn_index: int
    duration_minutes: float
    created_at: datetime
    last_activity: datetime


class AdminService:
    """Service for administrative operations and system monitoring."""

    def __init__(self, db_service: DatabaseService, session_manager: SessionManager):
        self._db = db_service
        self._sessions = session_manager

    async def list_all_players(self) -> List[AdminPlayerInfo]:
        players: List[Player] = await self._db.list_all_players(include_builtin=True)
        infos: List[AdminPlayerInfo] = []
        for p in players:
            win_rate = (p.wins / p.total_matches * 100.0) if p.total_matches > 0 else 0.0
            infos.append(
                AdminPlayerInfo(
                    player_id=p.player_id,
                    player_name=p.player_name,
                    submitted_from=p.submitted_from,
                    total_matches=p.total_matches,
                    wins=p.wins,
                    losses=p.losses,
                    draws=p.draws,
                    win_rate=win_rate,
                    created_at=p.created_at,
                    is_builtin=p.is_builtin,
                )
            )
        return infos

    async def get_active_sessions(self) -> List[AdminSessionInfo]:
        active_ids = await self._sessions.list_active_sessions()
        infos: List[AdminSessionInfo] = []
        for sid in active_ids:
            try:
                ctx = await self._sessions.get_session(sid)
            except Exception:
                continue
            started = ctx.created_at
            duration_minutes = (datetime.now() - started).total_seconds() / 60.0
            gs = ctx.game_state
            infos.append(
                AdminSessionInfo(
                    session_id=sid,
                    player_1_name=gs.player_1.player_name,
                    player_2_name=gs.player_2.player_name,
                    status=gs.status.value if isinstance(gs.status, TurnStatus) else str(gs.status),
                    turn_index=gs.turn_index,
                    duration_minutes=duration_minutes,
                    created_at=gs.created_at,
                    last_activity=gs.last_activity,
                )
            )
        return infos

    async def cleanup_session(self, session_id: str) -> bool:
        try:
            return await self._sessions.cleanup_session(session_id)
        except Exception as exc:
            logger.error(f"Failed to cleanup session {session_id}: {exc}")
            return False
