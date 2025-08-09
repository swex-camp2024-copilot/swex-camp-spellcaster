"""Bot client simulator for the Spellcasters Playground backend.

This module provides a realistic client that simulates an external player bot
process connecting to the backend API:

- Registers a player via REST
- Starts a match (e.g., vs a built-in bot)
- Connects to the SSE stream to consume turn updates
- (Placeholder) Submits actions when the action endpoint is available

Note: Action submission via API is planned in Task 7.1; this client exposes the
hook but defers implementation until the endpoint exists.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .sse_client import SSEClient, SSEClientConfig


logger = logging.getLogger(__name__)


# ----------------------------- Strategies ------------------------------------


class BotStrategy:
    """Strategy interface for deciding actions from game state."""

    async def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Return an action dict like {"move": [dx, dy], "spell": {...}|None}."""
        raise NotImplementedError


class RandomWalkStrategy(BotStrategy):
    """Very simple baseline strategy that drifts right/down and never casts spells."""

    def __init__(self) -> None:
        self._toggle = 1

    async def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self._toggle *= -1
        # Small deterministic walk; avoids randomness for reproducible tests
        return {"move": [self._toggle, max(0, self._toggle)], "spell": None}


# ----------------------------- Client ----------------------------------------


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
    """High-level client for registering, starting sessions, and streaming SSE."""

    def __init__(
        self,
        base_url: str,
        strategy: Optional[BotStrategy] = None,
        *,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.strategy = strategy or RandomWalkStrategy()
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    # -------------------------- Player Lifecycle --------------------------

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

    # -------------------------- Session Management ------------------------

    async def start_match_vs_builtin(self, player_id: str, builtin_bot_id: str) -> str:
        """Start a match between the given player (as player bot) and a built-in bot.

        The backend currently executes player bot decisions inside the server,
        so this returns a session_id for observing the match via SSE.
        """
        url = f"{self.base_url}/playground/start"
        payload = {
            "player_1_config": {"player_id": player_id, "bot_type": "player"},
            "player_2_config": {
                "player_id": f"builtin_{builtin_bot_id}",
                "bot_type": "builtin",
                "bot_id": builtin_bot_id,
            },
        }
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["session_id"]

    # -------------------------- Streaming ---------------------------------

    async def stream_session_events(
        self, session_id: str, *, max_events: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield events from the session SSE stream using the SSE client library."""
        cfg = SSEClientConfig()
        # Use the same HTTP client to ensure we use the same transport (ASGI vs HTTP)
        async with SSEClient(self.base_url, session_id, config=cfg, client=self._client).connect() as sse:
            count = 0
            async for event in sse.events():
                yield event
                count += 1
                if max_events is not None and count >= max_events:
                    break

    # -------------------------- Action Submission -------------------------

    async def submit_action(self, session_id: str, player_id: str, action: Dict[str, Any]) -> None:
        """Submit action for current turn. Placeholder until endpoint exists.

        Planned endpoint: POST /playground/{session_id}/action with JSON body
        {"player_id": str, "turn": int, "action_data": {...}}
        """
        raise NotImplementedError(
            "Action submission API not available yet (see Task 7.1)."
        )

    # -------------------------- Cleanup -----------------------------------

    async def aclose(self) -> None:
        if not self._external_client:
            await self._client.aclose()


__all__ = [
    "BotClient",
    "BotStrategy",
    "RandomWalkStrategy",
    "PlayerRegistrationRequest",
    "PlayerInfo",
]

