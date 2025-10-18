import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import create_tables


@pytest.mark.asyncio
async def test_start_endpoint_returns_session_id():
    await create_tables()

    payload = {
        "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
        "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
    }

    # Manually trigger lifespan to initialize state manager
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/playground/start", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data and isinstance(data["session_id"], str) and len(data["session_id"]) > 0
