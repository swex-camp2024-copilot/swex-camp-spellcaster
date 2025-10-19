"""Bot client simulator (moved from backend/client)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .sse_client import SSEClient, SSEClientConfig


logger = logging.getLogger(__name__)


class RandomWalkStrategy:
    """Simple bot that walks randomly for testing purposes.

    Implements BotInterface for compatibility.
    """

    def __init__(self) -> None:
        self._toggle = 1

    @property
    def name(self) -> str:
        """Return the bot's name."""
        return "RandomWalkStrategy"

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process game state and return action decision.

        Args:
            state: Game state containing turn, self, opponent, artifacts, minions

        Returns:
            Action dict with format: {"move": [dx, dy], "spell": None}
        """
        self._toggle *= -1
        return {"move": [self._toggle, max(0, self._toggle)], "spell": None}


class BotClient:
    """Client for interacting with the Spellcasters backend."""

    def __init__(self, base_url: str, bot_instance: Any, *, http_client: Optional[httpx.AsyncClient] = None) -> None:
        """Initialize BotClient with a bot implementation.

        Args:
            base_url: Backend server URL
            bot_instance: Bot implementation instance (must implement BotInterface)
            http_client: Optional external HTTP client
        """
        self.base_url = base_url.rstrip("/")
        self.bot = bot_instance
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    async def start_match(self, player_id: str, opponent_id: str, visualize: bool = True) -> str:
        """Start a match and return session ID.

        Automatically detects opponent type based on ID format:
        - IDs starting with 'builtin_' are builtin bots
        - Other IDs are remote players

        Args:
            player_id: Player ID (must be registered in backend)
            opponent_id: Opponent ID (builtin bot or remote player)
            visualize: Whether to enable Pygame visualizer

        Returns:
            Session ID string

        Raises:
            httpx.HTTPStatusError: If request fails (e.g., 404 for invalid player)
        """
        url = f"{self.base_url}/playground/start"

        # Configure player 1 (always remote player)
        player_1_config = {"player_id": player_id, "bot_type": "player"}

        # Configure player 2 based on opponent_id format
        if opponent_id.startswith("builtin_"):
            # For builtin bots, extract bot_id by replacing "builtin_" prefix with "sample_bot_"
            # e.g., "builtin_sample_1" -> "sample_bot_1"
            #       "builtin_tactical" -> "tactical_bot"
            if opponent_id.startswith("builtin_sample_"):
                # sample_1, sample_2, sample_3
                suffix = opponent_id[15:]  # Remove "builtin_sample_"
                bot_id = f"sample_bot_{suffix}"
            else:
                # tactical, rincewind, etc - add "_bot" suffix
                suffix = opponent_id[8:]  # Remove "builtin_"
                bot_id = f"{suffix}_bot" if not suffix.endswith("_bot") else suffix

            player_2_config = {
                "player_id": opponent_id,
                "bot_type": "builtin",
                "bot_id": bot_id,
            }
        else:
            # Remote player
            player_2_config = {"player_id": opponent_id, "bot_type": "player"}

        payload = {
            "player_1_config": player_1_config,
            "player_2_config": player_2_config,
            "visualize": visualize,
        }

        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["session_id"]

    async def stream_session_events(
        self, session_id: str, *, max_events: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        cfg = SSEClientConfig()
        async with SSEClient(self.base_url, session_id, config=cfg, client=self._client).connect() as sse:
            count = 0
            async for event in sse.events():
                yield event
                count += 1
                if max_events is not None and count >= max_events:
                    break

    async def submit_action(self, session_id: str, player_id: str, turn: int, action: Dict[str, Any]) -> None:
        """Submit an action for the current turn."""
        url = f"{self.base_url}/playground/{session_id}/action"
        payload = {"player_id": player_id, "turn": turn, "action_data": action}
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()

    async def play_match(
        self, session_id: str, player_id: str, *, max_events: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Play a match by streaming events and automatically submitting actions.

        This method combines event streaming with action submission. It:
        1. Listens to SSE events from the session
        2. When a turn_update event is received, extracts the game state
        3. Calls the bot's decide() method
        4. Submits the action to the backend
        5. Yields all events to the caller

        Args:
            session_id: The session ID
            player_id: The player ID
            max_events: Optional maximum number of events to process

        Yields:
            SSE events as dictionaries
        """
        async for event in self.stream_session_events(session_id, max_events=max_events):
            # Check if game is over - stop processing but yield the event
            if event.get("event") == "game_over":
                yield event
                break

            yield event

            # Check if this is a turn_update event
            if event.get("event") == "turn_update":
                game_state = event.get("game_state", {})

                try:
                    turn = event.get("turn", 0)
                    next_turn = turn + 1

                    # Call bot's decide() method directly (synchronous call in async context)
                    action = self.bot.decide(game_state)

                    logger.debug(f"Bot decided action for turn {next_turn}: {action}")

                    # Submit action for next turn
                    await self.submit_action(session_id, player_id, next_turn, action)
                    logger.info(f"Submitted action for turn {next_turn}")
                except Exception as e:
                    logger.error(
                        f"Failed to process turn {turn}: {e}",
                        exc_info=True,
                        extra={"game_state": game_state},
                    )
                    # Continue streaming - backend will use default action

    async def aclose(self) -> None:
        if not self._external_client:
            await self._client.aclose()


__all__ = [
    "BotClient",
    "RandomWalkStrategy",
]
