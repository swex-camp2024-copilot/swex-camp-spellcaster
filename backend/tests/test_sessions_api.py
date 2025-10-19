import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.database import create_tables
from backend.app.main import app


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


@pytest.mark.asyncio
async def test_start_endpoint_with_visualize_true():
    """Test that session creation succeeds with visualize=true."""
    await create_tables()

    payload = {
        "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
        "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        "visualize": True,
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/playground/start", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data and isinstance(data["session_id"], str) and len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_start_endpoint_with_visualize_false():
    """Test that session creation succeeds with visualize=false."""
    await create_tables()

    payload = {
        "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
        "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        "visualize": False,
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/playground/start", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data and isinstance(data["session_id"], str) and len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_start_endpoint_without_visualize_defaults_to_false():
    """Test that visualize parameter defaults to false when not provided."""
    await create_tables()

    payload = {
        "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
        "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        # visualize not specified - should default to False
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/playground/start", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data and isinstance(data["session_id"], str) and len(data["session_id"]) > 0
