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
    def __init__(self, base_url: str, strategy: Optional[BotStrategy] = None, *, http_client: Optional[httpx.AsyncClient] = None) -> None:
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

    async def start_match_vs_builtin(self, player_id: str, builtin_bot_id: str) -> str:
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

    async def stream_session_events(self, session_id: str, *, max_events: Optional[int] = None) -> AsyncIterator[Dict[str, Any]]:
        cfg = SSEClientConfig()
        async with SSEClient(self.base_url, session_id, config=cfg, client=self._client).connect() as sse:
            count = 0
            async for event in sse.events():
                yield event
                count += 1
                if max_events is not None and count >= max_events:
                    break

    async def submit_action(self, session_id: str, player_id: str, action: Dict[str, Any]) -> None:
        raise NotImplementedError("Action submission API not available yet (see Task 7.1).")

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


