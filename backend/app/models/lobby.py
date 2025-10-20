"""Lobby system data models for PvP matchmaking."""

import asyncio
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .players import PlayerConfig


class LobbyJoinRequest(BaseModel):
    """Request to join the lobby queue."""

    player_id: str = Field(..., description="Player ID joining the lobby")
    bot_config: PlayerConfig = Field(..., description="Bot configuration for this player")


class LobbyMatchResponse(BaseModel):
    """Response when a lobby match is found."""

    session_id: str = Field(..., description="Created session ID")
    opponent_id: str = Field(..., description="Matched opponent's player ID")
    opponent_name: str = Field(..., description="Matched opponent's display name")


class QueueEntry:
    """Internal queue entry for lobby system (not a Pydantic model due to asyncio.Event).

    This class manages the state of a player waiting in the lobby queue.
    """

    def __init__(self, player_id: str, bot_config: PlayerConfig):
        """Initialize queue entry.

        Args:
            player_id: Player's unique identifier
            bot_config: Player's bot configuration
        """
        self.player_id = player_id
        self.bot_config = bot_config
        self.joined_at = datetime.now()
        self.event: asyncio.Event = asyncio.Event()
        self.session_id: Optional[str] = None
        self.opponent_id: Optional[str] = None
        self.opponent_name: Optional[str] = None

    def set_match_result(self, session_id: str, opponent_id: str, opponent_name: str) -> None:
        """Set the match result and signal the waiting coroutine.

        Args:
            session_id: ID of the created session
            opponent_id: Matched opponent's player ID
            opponent_name: Matched opponent's display name
        """
        self.session_id = session_id
        self.opponent_id = opponent_id
        self.opponent_name = opponent_name
        self.event.set()

    async def wait_for_match(self) -> LobbyMatchResponse:
        """Wait for a match to be found (long-polling).

        Returns:
            LobbyMatchResponse with session and opponent details

        Raises:
            RuntimeError: If match result was not set before event was triggered
        """
        await self.event.wait()

        if self.session_id is None or self.opponent_id is None or self.opponent_name is None:
            raise RuntimeError("Match event was set but match result was not populated")

        return LobbyMatchResponse(
            session_id=self.session_id, opponent_id=self.opponent_id, opponent_name=self.opponent_name
        )
