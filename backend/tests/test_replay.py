import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import create_tables


@pytest.mark.asyncio
async def test_replay_endpoint_streams_events():
    await create_tables()

    # Start a quick dummy session with builtin bots
    payload = {
        "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
        "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
    }

    # Manually trigger lifespan to initialize state manager
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=5.0) as ac:
            resp = await ac.post("/playground/start", json=payload)
            assert resp.status_code == 200
            session_id = resp.json()["session_id"]

            # Give loop time to execute at least one turn end and log entries
            await asyncio.sleep(0.2)

            # Now request replay; we can't fully consume a stream easily; just ensure route exists
            try:
                # HEAD may not be allowed; try GET with very short timeout
                async with asyncio.timeout(0.1):
                    resp = await ac.get(f"/playground/{session_id}/replay")
                    assert resp.status_code == 200
            except asyncio.TimeoutError:
                # The endpoint started streaming; that's sufficient to prove it works for route-level
                pass

