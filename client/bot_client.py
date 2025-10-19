"""Bot client simulator (moved from backend/client)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .sse_client import SSEClient, SSEClientConfig


logger = logging.getLogger(__name__)


class BotStrategy:
    async def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class RandomWalkStrategy(BotStrategy):
    def __init__(self) -> None:
        self._toggle = 1

    async def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self._toggle *= -1
        return {"move": [self._toggle, max(0, self._toggle)], "spell": None}


class BotInterfaceAdapter(BotStrategy):
    """Adapter to wrap BotInterface instances for use with BotClient."""

    def __init__(self, bot_instance: Any) -> None:
        """Initialize with a BotInterface instance.

        Args:
            bot_instance: An instance of a class implementing BotInterface
        """
        self._bot = bot_instance

    async def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Call the bot's decide method (sync) and return the result.

        Args:
            state: Game state dictionary

        Returns:
            Action dictionary with move and spell
        """
        # BotInterface.decide() is synchronous, but we run it in async context
        return self._bot.decide(state)


@dataclass
class PlayerRegistrationRequest:
    player_name: str
    submitted_from: str = "online"
    sprite_path: Optional[str] = None
    minion_sprite_path: Optional[str] = None


@dataclass
class PlayerInfo:
    player_id: str
    player_name: str


class BotClient:
    def __init__(
        self, base_url: str, strategy: Optional[BotStrategy] = None, *, http_client: Optional[httpx.AsyncClient] = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.strategy = strategy or RandomWalkStrategy()
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    async def register_player(self, req: PlayerRegistrationRequest) -> PlayerInfo:
        url = f"{self.base_url}/players/register"
        payload = {
            "player_name": req.player_name,
            "submitted_from": req.submitted_from,
            "sprite_path": req.sprite_path,
            "minion_sprite_path": req.minion_sprite_path,
        }
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return PlayerInfo(player_id=data["player_id"], player_name=data["player_name"])

    async def start_match_vs_builtin(self, player_id: str, builtin_bot_id: str, max_events: int = 100) -> str:
        url = f"{self.base_url}/playground/start"
        payload = {
            "player_1_config": {"player_id": player_id, "bot_type": "player"},
            "player_2_config": {
                "player_id": f"builtin_{builtin_bot_id}",
                "bot_type": "builtin",
                "bot_id": builtin_bot_id,
            },
            "max_events": max_events,
            "visualize": True,
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
        3. Calls the bot strategy's decide() method
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
            yield event

            # Check if this is a turn_update event and if it's our turn
            if event.get("event") == "turn_update":
                game_state = event.get("game_state", {})

                # Determine if it's our turn by checking whose turn it is
                # The game state contains information about which player needs to act
                # For simplicity, we submit an action on every turn_update
                try:
                    turn = event.get("turn", 0)
                    next_turn = turn + 1

                    # Get action from strategy
                    action = await self.strategy.decide(game_state)

                    # Submit action for next turn
                    logger.info(f"Submitting action for turn {next_turn}: {action}")
                    await self.submit_action(session_id, player_id, next_turn, action)
                except Exception as e:
                    logger.error(f"Failed to submit action: {e}", exc_info=True)

    async def aclose(self) -> None:
        if not self._external_client:
            await self._client.aclose()


__all__ = [
    "BotClient",
    "BotStrategy",
    "RandomWalkStrategy",
    "BotInterfaceAdapter",
    "PlayerRegistrationRequest",
    "PlayerInfo",
]
