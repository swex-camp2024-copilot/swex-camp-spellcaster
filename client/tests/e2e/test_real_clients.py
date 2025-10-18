"""End-to-end tests using real SSE and bot clients (in-process via ASGI)."""

import asyncio
from typing import Dict, Any

import pytest
from httpx import AsyncClient, ASGITransport, Timeout

from backend.app.main import app
from backend.app.core.database import create_tables

# Support running as package or script
try:
    from client.sse_client import SSEClient, SSEClientConfig  # type: ignore
except Exception:  # pragma: no cover
    from ...client.sse_client import SSEClient, SSEClientConfig  # type: ignore

try:
    from client.bot_client import (
        BotClient,
        PlayerRegistrationRequest,
    )  # type: ignore
except Exception:  # pragma: no cover
    from ...client.bot_client import BotClient, PlayerRegistrationRequest  # type: ignore


def _asgi_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=Timeout(5.0))


@pytest.mark.asyncio
async def test_sse_client_streams_events_with_asgi_transport():
    await create_tables()

    async with _asgi_client() as ac:
        # Use SSE client with the same underlying httpx client
        cfg = SSEClientConfig()

        # Start a builtin vs builtin session
        payload = {
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        }
        resp = await ac.post("/playground/start", json=payload)
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        sse_client = SSEClient("http://test", session_id, config=cfg, client=ac)

        async with sse_client.connect():

            async def read_first_event():
                async for ev in sse_client.events():
                    assert isinstance(ev, dict)
                    assert "event" in ev
                    return ev

            ev = await asyncio.wait_for(read_first_event(), timeout=10.0)
            assert ev["event"] in ("heartbeat", "turn_update")


@pytest.mark.asyncio
async def test_bot_client_register_start_and_stream():
    await create_tables()

    async with _asgi_client() as ac:
        # Test BotClient functionality: register player and start match
        bot = BotClient("http://test", http_client=ac)
        player = await bot.register_player(PlayerRegistrationRequest(player_name="E2E Bot"))
        assert player.player_id is not None
        assert player.player_name == "E2E Bot"

        # BotClient can start a match vs builtin
        session_id = await bot.start_match_vs_builtin(player.player_id, "sample_bot_1")
        assert session_id is not None
        assert len(session_id) > 0


@pytest.mark.asyncio
async def test_concurrent_sessions_isolation():
    await create_tables()

    async with _asgi_client() as ac:
        # Start two sessions
        payload1 = {
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        }
        payload2 = {
            "player_1_config": {"player_id": "builtin_sample_3", "bot_type": "builtin", "bot_id": "sample_bot_3"},
            "player_2_config": {"player_id": "builtin_tactical", "bot_type": "builtin", "bot_id": "tactical_bot"},
        }
        r1 = await ac.post("/playground/start", json=payload1)
        r2 = await ac.post("/playground/start", json=payload2)
        assert r1.status_code == 200 and r2.status_code == 200
        s1 = r1.json()["session_id"]
        s2 = r2.json()["session_id"]

        c1 = SSEClient("http://test", s1, client=ac, config=SSEClientConfig())
        c2 = SSEClient("http://test", s2, client=ac, config=SSEClientConfig())

        async def first_event(client: SSEClient):
            async with client.connect():
                async for ev in client.events():
                    return ev

        e1, e2 = await asyncio.wait_for(asyncio.gather(first_event(c1), first_event(c2)), timeout=10.0)
        assert isinstance(e1, dict) and "event" in e1
        assert isinstance(e2, dict) and "event" in e2
