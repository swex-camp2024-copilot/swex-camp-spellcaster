import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import create_tables


@pytest.mark.asyncio
async def test_streaming_endpoint_exists():
    await create_tables()

    # Start a session first
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

            # Test that the SSE endpoint exists for a valid session (just check it doesn't 404)
            # We can't easily test the actual streaming without hanging, so just verify route exists
            try:
                # Use head request to avoid triggering the streaming response
                resp = await ac.head(f"/playground/{session_id}/events")
                # If head isn't supported, at least we know the route exists
                assert resp.status_code in [200, 405]  # 405 = Method Not Allowed but route exists
            except Exception:
                # If head fails, try GET with very short timeout to prove route exists
                try:
                    async with asyncio.timeout(0.1):
                        resp = await ac.get(f"/playground/{session_id}/events")
                        assert resp.status_code == 200
                except asyncio.TimeoutError:
                    # Expected - proves the route exists and started streaming
                    pass
