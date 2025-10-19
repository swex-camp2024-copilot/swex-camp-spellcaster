import uuid

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


@pytest.mark.asyncio
async def test_start_endpoint_with_player_bot_type():
    """Test session creation with bot_type='player' for remote player."""
    await create_tables()

    # First register a player
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Register player
            player_payload = {"player_name": f"Test Player {uuid.uuid4().hex[:8]}", "submitted_from": "online"}
            player_resp = await ac.post("/players/register", json=player_payload)
            assert player_resp.status_code == 201
            player_id = player_resp.json()["player_id"]

            # Start session with remote player vs builtin bot
            session_payload = {
                "player_1_config": {"player_id": player_id, "bot_type": "player"},
                "player_2_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
                "visualize": False,
            }
            resp = await ac.post("/playground/start", json=session_payload)
            assert resp.status_code == 200
            data = resp.json()
            assert "session_id" in data
            assert isinstance(data["session_id"], str)
            assert len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_start_endpoint_player_not_found():
    """Test session creation fails with 404 when player does not exist."""
    await create_tables()

    payload = {
        "player_1_config": {"player_id": "nonexistent-player-id", "bot_type": "player"},
        "player_2_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
        "visualize": False,
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/playground/start", json=payload)
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_start_endpoint_player_vs_player():
    """Test session creation with two remote players (PvP)."""
    await create_tables()

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Register two players
            player1_payload = {"player_name": f"Player 1 {uuid.uuid4().hex[:8]}", "submitted_from": "online"}
            player1_resp = await ac.post("/players/register", json=player1_payload)
            assert player1_resp.status_code == 201
            player1_id = player1_resp.json()["player_id"]

            player2_payload = {"player_name": f"Player 2 {uuid.uuid4().hex[:8]}", "submitted_from": "online"}
            player2_resp = await ac.post("/players/register", json=player2_payload)
            assert player2_resp.status_code == 201
            player2_id = player2_resp.json()["player_id"]

            # Start PvP session
            session_payload = {
                "player_1_config": {"player_id": player1_id, "bot_type": "player"},
                "player_2_config": {"player_id": player2_id, "bot_type": "player"},
                "visualize": False,
            }
            resp = await ac.post("/playground/start", json=session_payload)
            assert resp.status_code == 200
            data = resp.json()
            assert "session_id" in data
            assert isinstance(data["session_id"], str)
            assert len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_start_endpoint_builtin_bot_missing_bot_id():
    """Test session creation fails with 400 when bot_id is missing for builtin bot."""
    await create_tables()

    payload = {
        "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin"},  # Missing bot_id
        "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        "visualize": False,
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/playground/start", json=payload)
            assert resp.status_code == 400
            assert "bot_id" in resp.json()["detail"].lower()
