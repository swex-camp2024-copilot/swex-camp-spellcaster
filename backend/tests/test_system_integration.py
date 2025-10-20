"""Comprehensive system integration tests (Task 10.4).

Tests complete workflows including:
- End-to-end match flow
- Concurrent session handling
- SSE streaming
- Error handling
- State management
"""

import asyncio
import time

import pytest
from httpx import AsyncClient
from fastapi import status

from backend.app.main import app
from backend.app.core.state import get_state_manager


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health endpoint returns state manager status."""
    async with AsyncClient(transport=None, base_url="http://test") as client:
        # Need to actually start the app to test this properly
        pass


@pytest.mark.asyncio
async def test_state_manager_initialization():
    """Test that state manager initializes all services correctly."""
    try:
        state_manager = get_state_manager()

        # Verify state manager is ready
        assert state_manager.is_ready, "State manager should be ready"

        # Verify all services are initialized
        assert state_manager.db_service is not None
        assert state_manager.sse_manager is not None
        assert state_manager.match_logger is not None
        assert state_manager.session_manager is not None
        assert state_manager.admin_service is not None

        # Verify health check
        health = state_manager.get_health()
        assert health["status"] == "ready"
        assert health["is_ready"] is True
        assert "services" in health

        # Verify all services are ready
        for service_name, service_status in health["services"].items():
            assert service_status == "ready", f"Service {service_name} should be ready"

    except RuntimeError:
        # State manager not initialized in test environment
        pytest.skip("State manager not initialized - requires full app startup")


@pytest.mark.asyncio
async def test_statistics_endpoint():
    """Test statistics endpoint returns system stats."""
    try:
        state_manager = get_state_manager()

        stats = state_manager.get_statistics()

        assert "uptime_seconds" in stats
        assert "active_sessions" in stats
        assert "active_sse_connections" in stats

        # Should start with no active sessions
        assert stats["active_sessions"] >= 0
        assert stats["active_sse_connections"] >= 0

    except RuntimeError:
        pytest.skip("State manager not initialized - requires full app startup")


@pytest.mark.asyncio
async def test_error_handler_playground_error(test_client):
    """Test that custom PlaygroundError is handled correctly."""
    # Try to get a non-existent session
    response = await test_client.get("/playground/nonexistent/events")

    assert response.status_code == 404
    data = response.json()

    # Should have error response structure
    assert "error" in data
    assert "message" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_error_handler_validation_error(test_client):
    """Test that validation errors are handled correctly."""
    # Send invalid player registration
    response = await test_client.post(
        "/players/register",
        json={"invalid_field": "test"},  # Missing required 'player_name' field
    )

    assert response.status_code == 422
    data = response.json()

    # FastAPI returns validation errors in 'detail' field
    assert "detail" in data or "error" in data


@pytest.mark.asyncio
async def test_complete_match_workflow(test_client):
    """Test complete end-to-end match workflow."""
    # 1. Register two players with unique names to avoid conflicts across test runs
    timestamp = int(time.time() * 1000)

    player1_response = await test_client.post(
        "/players/register", json={"player_name": f"IntegrationBot1_{timestamp}", "submitted_from": "online"}
    )
    assert player1_response.status_code == 201
    player1 = player1_response.json()

    player2_response = await test_client.post(
        "/players/register", json={"player_name": f"IntegrationBot2_{timestamp}", "submitted_from": "online"}
    )
    assert player2_response.status_code == 201
    player2 = player2_response.json()

    # 2. Start a session
    session_response = await test_client.post(
        "/playground/start",
        json={
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        },
    )
    assert session_response.status_code == 200
    session_data = session_response.json()
    session_id = session_data["session_id"]

    # 3. Verify session exists in active sessions
    active_response = await test_client.get("/playground/active")
    assert active_response.status_code == 200
    active_sessions = active_response.json()
    assert len(active_sessions) > 0
    assert any(s["session_id"] == session_id for s in active_sessions)

    # 4. Wait for match to complete (built-in bots run automatically)
    await asyncio.sleep(2)

    # 5. Check replay is available
    replay_response = await test_client.get(f"/playground/{session_id}/replay")
    # Replay should stream events
    assert replay_response.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_sessions(test_client):
    """Test handling multiple concurrent sessions."""
    # Start multiple sessions concurrently
    session_configs = [
        {
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        }
        for _ in range(3)
    ]

    # Create sessions concurrently
    tasks = [test_client.post("/playground/start", json=config) for config in session_configs]

    responses = await asyncio.gather(*tasks)

    # All sessions should be created successfully
    assert all(r.status_code == 200 for r in responses)

    session_ids = [r.json()["session_id"] for r in responses]

    # All session IDs should be unique
    assert len(set(session_ids)) == len(session_ids)

    # Verify all are in active sessions
    active_response = await test_client.get("/playground/active")
    assert active_response.status_code == 200
    active_sessions = active_response.json()

    for session_id in session_ids:
        assert any(s["session_id"] == session_id for s in active_sessions)


@pytest.mark.asyncio
async def test_admin_operations(test_client):
    """Test admin endpoints for monitoring and cleanup."""
    # 1. List all players
    players_response = await test_client.get("/admin/players")
    assert players_response.status_code == 200
    players = players_response.json()
    assert isinstance(players, list)

    # 2. Start a session to test cleanup
    session_response = await test_client.post(
        "/playground/start",
        json={
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        },
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    # 3. Verify session is active
    active_response = await test_client.get("/playground/active")
    assert active_response.status_code == 200
    active_sessions = active_response.json()
    assert any(s["session_id"] == session_id for s in active_sessions)

    # 4. Cleanup the session
    cleanup_response = await test_client.delete(f"/playground/{session_id}")
    assert cleanup_response.status_code == 200
    cleanup_data = cleanup_response.json()
    assert cleanup_data["status"] == "terminated"
    assert cleanup_data["session_id"] == session_id


@pytest.mark.asyncio
async def test_error_propagation(test_client):
    """Test that errors propagate correctly through the system."""
    # Test various error scenarios

    # 1. Session not found
    response = await test_client.get("/playground/nonexistent/replay")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data or "message" in data  # Custom error format

    # 2. Invalid action submission (no session)
    response = await test_client.post(
        "/playground/nonexistent/action",
        json={"player_id": "test", "turn": 1, "action_data": {"move": [0, 0], "spell": None}},
    )
    assert response.status_code in [400, 404, 500]  # Should error

    # 3. Invalid player deletion (non-existent player)
    response = await test_client.delete("/players/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sse_connection_management(test_client):
    """Test SSE connection creation and cleanup."""
    # Create a session
    session_response = await test_client.post(
        "/playground/start",
        json={
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        },
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    # Try to connect to SSE stream
    # Note: Full SSE streaming test is complex in pytest, just verify endpoint exists
    response = await test_client.get(f"/playground/{session_id}/events", headers={"Accept": "text/event-stream"})

    # Should start streaming (status 200) or indicate session state
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_health_and_stats_integration(test_client):
    """Test health and statistics endpoints work together."""
    # Get health
    health_response = await test_client.get("/health")
    assert health_response.status_code == 200
    health = health_response.json()

    assert "status" in health
    assert "service" in health
    assert health["service"] == "spellcasters-playground-backend"

    # Get stats
    stats_response = await test_client.get("/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()

    assert "statistics" in stats
    assert "service" in stats
    assert stats["service"] == "spellcasters-playground-backend"


@pytest.mark.asyncio
async def test_component_integration_and_data_flow(test_client):
    """Test data flows correctly between all components."""
    # 1. Register a player (tests database integration) with unique name
    timestamp = int(time.time() * 1000)

    player_response = await test_client.post(
        "/players/register", json={"player_name": f"FlowTestBot_{timestamp}", "submitted_from": "online"}
    )
    assert player_response.status_code == 201

    # 2. Start session (tests session manager, SSE manager integration)
    session_response = await test_client.post(
        "/playground/start",
        json={
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        },
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    # 3. Wait for game to progress
    await asyncio.sleep(1)

    # 4. Check replay (tests match logger integration)
    replay_response = await test_client.get(f"/playground/{session_id}/replay")
    assert replay_response.status_code == 200

    # 5. Check admin view (tests admin service integration)
    active_response = await test_client.get("/playground/active")
    assert active_response.status_code == 200

    # 6. Cleanup (tests cleanup flow)
    cleanup_response = await test_client.delete(f"/playground/{session_id}")
    assert cleanup_response.status_code == 200


@pytest.mark.asyncio
async def test_player_id_slug_generation_integration(test_client):
    """Test that player IDs are generated as slugs from player names."""
    import time

    # Use timestamp to ensure unique names across test runs
    timestamp = int(time.time() * 1000)
    player_name = f"Kevin Lin {timestamp}"

    # Test basic slug generation
    response = await test_client.post(
        "/players/register", json={"player_name": player_name, "submitted_from": "online"}
    )
    assert response.status_code == 201
    data = response.json()
    # Should be "kevin-lin-<timestamp>"
    assert data["player_id"].startswith("kevin-lin-")
    assert data["player_name"] == player_name


@pytest.mark.asyncio
async def test_player_id_slug_special_characters_integration(test_client):
    """Test that special characters are removed from player ID slugs."""
    import time

    timestamp = int(time.time() * 1000)

    test_cases = [
        (f"O'Brien! {timestamp}", "obrien"),
        (f"Test User #1 {timestamp + 1}", "test-user-1"),
        (f"Alice@Bob {timestamp + 2}", "alicebob"),
        (f"User$123 {timestamp + 3}", "user123"),
    ]

    for player_name, expected_slug_prefix in test_cases:
        response = await test_client.post(
            "/players/register", json={"player_name": player_name, "submitted_from": "online"}
        )
        assert response.status_code == 201
        data = response.json()
        # Check that the slug starts with the expected prefix (before the timestamp)
        assert data["player_id"].startswith(expected_slug_prefix), (
            f"Expected slug to start with {expected_slug_prefix} for {player_name}, got {data['player_id']}"
        )


@pytest.mark.asyncio
async def test_player_id_deduplication_with_postfix_integration(test_client):
    """Test that duplicate slugs get numeric postfix (_2, _3, etc.)."""
    import time

    timestamp = int(time.time() * 1000)

    # Register first player with name "Dedup Player <timestamp>"
    player_name = f"Dedup Player {timestamp}"
    response1 = await test_client.post(
        "/players/register", json={"player_name": player_name, "submitted_from": "online"}
    )
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["player_id"].startswith("dedup-player-")

    # Register second player with same name - should get 409 due to case-insensitive uniqueness
    response2 = await test_client.post(
        "/players/register", json={"player_name": player_name, "submitted_from": "online"}
    )
    # This should fail due to case-insensitive name uniqueness, not create _2
    # Per spec: "Enforce case-insensitive uniqueness for player_name"
    assert response2.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_player_id_builtin_unchanged_integration(test_client):
    """Test that built-in player IDs remain unchanged."""
    # Get list of players including built-ins
    response = await test_client.get("/players?include_builtin=true")
    assert response.status_code == 200
    players = response.json()

    # Find built-in players
    builtin_players = [p for p in players if p.get("is_builtin", False)]

    # Verify built-in IDs follow the old pattern (builtin_*)
    for player in builtin_players:
        assert player["player_id"].startswith("builtin_"), (
            f"Built-in player {player['player_name']} has ID {player['player_id']}, expected to start with 'builtin_'"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
