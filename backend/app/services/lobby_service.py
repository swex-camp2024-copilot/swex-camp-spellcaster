"""Lobby service for PvP matchmaking with FIFO queue and long-polling."""

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING, Deque, Dict, Optional

from ..core.exceptions import PlayerAlreadyInLobbyError, PlayerNotFoundError
from ..models.lobby import LobbyJoinRequest, LobbyMatchResponse, QueueEntry

if TYPE_CHECKING:
    from .database import DatabaseService
    from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class LobbyService:
    """Manages lobby queue for PvP matchmaking.

    Uses FIFO queue for fair matching. When 2+ players are in queue,
    automatically creates a session and notifies both players via long-polling.
    """

    def __init__(
        self, session_manager: Optional["SessionManager"] = None, db_service: Optional["DatabaseService"] = None
    ):
        """Initialize lobby service.

        Args:
            session_manager: SessionManager instance for creating matches
            db_service: DatabaseService for player lookups
        """
        self._session_manager = session_manager
        self._db = db_service
        self._queue: Deque[QueueEntry] = deque()
        self._player_lookup: Dict[str, QueueEntry] = {}
        self._lock = asyncio.Lock()

    def set_session_manager(self, session_manager: "SessionManager") -> None:
        """Set the session manager (for deferred initialization)."""
        self._session_manager = session_manager

    def set_database_service(self, db_service: "DatabaseService") -> None:
        """Set the database service (for deferred initialization)."""
        self._db = db_service

    async def join_queue(self, request: LobbyJoinRequest) -> LobbyMatchResponse:
        """Join lobby queue and wait for match (long-polling).

        This method blocks until a match is found. When 2+ players are in queue,
        they are automatically matched and a session is created.

        Args:
            request: Lobby join request with player_id and bot_config

        Returns:
            LobbyMatchResponse with session_id and opponent details

        Raises:
            PlayerAlreadyInLobbyError: If player is already in queue
            PlayerNotFoundError: If player_id doesn't exist in database
            RuntimeError: If session_manager or db_service not set
        """
        if self._session_manager is None:
            raise RuntimeError("SessionManager not set on LobbyService")
        if self._db is None:
            raise RuntimeError("DatabaseService not set on LobbyService")

        # Verify player exists
        player = await self._db.get_player(request.player_id)
        if not player:
            raise PlayerNotFoundError(request.player_id)

        async with self._lock:
            # Check if already in queue
            if request.player_id in self._player_lookup:
                raise PlayerAlreadyInLobbyError(request.player_id)

            # Create queue entry
            entry = QueueEntry(player_id=request.player_id, bot_config=request.bot_config)
            self._queue.append(entry)
            self._player_lookup[request.player_id] = entry

            queue_position = len(self._queue)
            logger.info(f"Player {request.player_id} joined lobby queue (position {queue_position})")

        # Try to match immediately (releases lock first)
        await self._try_match()

        # Wait for match (long-polling)
        logger.debug(f"Player {request.player_id} waiting for match...")
        match_response = await entry.wait_for_match()
        logger.info(
            f"Player {request.player_id} matched! Session: {match_response.session_id}, "
            f"Opponent: {match_response.opponent_id}"
        )

        return match_response

    async def _try_match(self) -> None:
        """Attempt to match first 2 players in queue.

        If 2+ players are waiting, creates a session with visualization enabled
        and notifies both players.
        """
        async with self._lock:
            if len(self._queue) < 2:
                logger.debug(f"Not enough players to match ({len(self._queue)} in queue)")
                return

            # Pop first 2 players (FIFO)
            p1_entry = self._queue.popleft()
            p2_entry = self._queue.popleft()

            # Remove from lookup
            del self._player_lookup[p1_entry.player_id]
            del self._player_lookup[p2_entry.player_id]

            logger.info(f"Matching players: {p1_entry.player_id} vs {p2_entry.player_id}")

        # Create session outside the lock to avoid blocking queue operations
        try:
            # Get player names for response
            p1_player = await self._db.get_player(p1_entry.player_id)
            p2_player = await self._db.get_player(p2_entry.player_id)

            if not p1_player or not p2_player:
                logger.error(f"Player not found during matching: p1={p1_player}, p2={p2_player}")
                return

            # Create session with visualization enabled
            session_id = await self._session_manager.create_session(
                player_1=p1_entry.bot_config, player_2=p2_entry.bot_config, visualize=True
            )

            logger.info(f"Created lobby match session: {session_id}")

            # Notify both players (unblocks their long-polling requests)
            p1_entry.set_match_result(
                session_id=session_id, opponent_id=p2_entry.player_id, opponent_name=p2_player.player_name
            )
            p2_entry.set_match_result(
                session_id=session_id, opponent_id=p1_entry.player_id, opponent_name=p1_player.player_name
            )

        except Exception as e:
            logger.error(f"Failed to create session for lobby match: {e}", exc_info=True)
            # TODO: Consider re-queuing players or notifying them of the error

    async def get_queue_size(self) -> int:
        """Get current number of players waiting in queue.

        Returns:
            Number of players in queue
        """
        async with self._lock:
            return len(self._queue)

    async def get_player_position(self, player_id: str) -> Optional[int]:
        """Get player's position in queue (1-indexed).

        Args:
            player_id: Player to check

        Returns:
            Position in queue (1 = first), or None if not in queue
        """
        async with self._lock:
            if player_id not in self._player_lookup:
                return None

            # Find position in queue
            for i, entry in enumerate(self._queue, start=1):
                if entry.player_id == player_id:
                    return i

            return None

    async def remove_from_queue(self, player_id: str) -> bool:
        """Remove a player from the queue.

        Args:
            player_id: Player to remove

        Returns:
            True if player was removed, False if not in queue
        """
        async with self._lock:
            if player_id not in self._player_lookup:
                return False

            entry = self._player_lookup[player_id]
            self._queue.remove(entry)
            del self._player_lookup[player_id]

            logger.info(f"Removed player {player_id} from lobby queue")
            return True
