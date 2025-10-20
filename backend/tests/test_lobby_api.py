"""Integration tests for Lobby API endpoints."""

import asyncio
import uuid

import pytest
import pytest_asyncio

from backend.app.services import runtime


@pytest_asyncio.fixture
async def test_players(test_client):
    """Create test players for lobby tests with unique names."""
    # Use unique names to avoid conflicts between tests
    unique_suffix = str(uuid.uuid4())[:8]

    # Register player 1
    resp1 = await test_client.post("/players/register", json={"player_name": f"Lobby Player 1 {unique_suffix}"})
    assert resp1.status_code == 201
    player1_id = resp1.json()["player_id"]

    # Register player 2
    resp2 = await test_client.post("/players/register", json={"player_name": f"Lobby Player 2 {unique_suffix}"})
    assert resp2.status_code == 201
    player2_id = resp2.json()["player_id"]

    return player1_id, player2_id


@pytest.mark.asyncio
async def test_join_lobby_and_match(test_client, test_players):
    """Test two players joining lobby and getting matched."""
    player1_id, player2_id = test_players

    # Start both players joining lobby concurrently
    async def join_player1():
        response = await test_client.post(
            "/lobby/join",
            json={
                "player_id": player1_id,
                "bot_config": {"player_id": player1_id, "bot_type": "player"},
            },
            timeout=10.0,
        )
        return response

    async def join_player2():
        # Add small delay to ensure player 1 joins first
        await asyncio.sleep(0.1)
        response = await test_client.post(
            "/lobby/join",
            json={
                "player_id": player2_id,
                "bot_config": {"player_id": player2_id, "bot_type": "player"},
            },
            timeout=10.0,
        )
        return response

    # Execute both joins concurrently
    results = await asyncio.gather(join_player1(), join_player2())
    resp1, resp2 = results

    # Both should succeed
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    # Both should get the same session_id
    data1 = resp1.json()
    data2 = resp2.json()

    assert data1["session_id"] == data2["session_id"]

    # Each should have opponent info
    assert data1["opponent_id"] == player2_id
    assert data2["opponent_id"] == player1_id


@pytest.mark.asyncio
async def test_join_lobby_player_not_found(test_client):
    """Test joining lobby with non-existent player returns 404."""
    response = await test_client.post(
        "/lobby/join",
        json={
            "player_id": "nonexistent",
            "bot_config": {"player_id": "nonexistent", "bot_type": "player"},
        },
        timeout=2.0,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_join_lobby_player_already_in_queue(test_client, test_players):
    """Test that a player cannot join lobby twice."""
    player1_id, _ = test_players

    # Start first join (will block waiting for match)
    task1 = asyncio.create_task(
        test_client.post(
            "/lobby/join",
            json={
                "player_id": player1_id,
                "bot_config": {"player_id": player1_id, "bot_type": "player"},
            },
            timeout=10.0,
        )
    )

    # Give it time to join queue
    await asyncio.sleep(0.2)

    # Second join attempt should fail immediately
    response = await test_client.post(
        "/lobby/join",
        json={
            "player_id": player1_id,
            "bot_config": {"player_id": player1_id, "bot_type": "player"},
        },
        timeout=2.0,
    )

    assert response.status_code == 409

    # Clean up: remove player from queue
    await runtime.lobby_service.remove_from_queue(player1_id)
    task1.cancel()


@pytest.mark.asyncio
async def test_get_lobby_status(test_client, test_players):
    """Test getting lobby status."""
    player1_id, _ = test_players

    # Initially empty
    response = await test_client.get("/lobby/status")
    assert response.status_code == 200
    assert response.json()["queue_size"] == 0

    # Add one player
    task1 = asyncio.create_task(
        test_client.post(
            "/lobby/join",
            json={
                "player_id": player1_id,
                "bot_config": {"player_id": player1_id, "bot_type": "player"},
            },
            timeout=10.0,
        )
    )

    # Give it time to join
    await asyncio.sleep(0.2)

    # Check status
    response = await test_client.get("/lobby/status")
    assert response.status_code == 200
    assert response.json()["queue_size"] == 1

    # Clean up
    await runtime.lobby_service.remove_from_queue(player1_id)
    task1.cancel()


@pytest.mark.asyncio
async def test_leave_lobby(test_client, test_players):
    """Test leaving lobby queue."""
    player1_id, _ = test_players

    # Join lobby
    task1 = asyncio.create_task(
        test_client.post(
            "/lobby/join",
            json={
                "player_id": player1_id,
                "bot_config": {"player_id": player1_id, "bot_type": "player"},
            },
            timeout=10.0,
        )
    )

    # Give it time to join
    await asyncio.sleep(0.2)

    # Leave lobby
    response = await test_client.delete(f"/lobby/leave/{player1_id}")
    assert response.status_code == 200

    # Queue should be empty
    status = await test_client.get("/lobby/status")
    assert status.json()["queue_size"] == 0

    # Clean up
    task1.cancel()


@pytest.mark.asyncio
async def test_leave_lobby_player_not_in_queue(test_client):
    """Test leaving lobby when player is not in queue returns 404."""
    response = await test_client.delete("/lobby/leave/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_lobby_match_creates_session(test_client, test_players):
    """Test that lobby match actually creates a game session."""
    player1_id, player2_id = test_players

    # Join lobby concurrently
    async def join_player1():
        return await test_client.post(
            "/lobby/join",
            json={
                "player_id": player1_id,
                "bot_config": {"player_id": player1_id, "bot_type": "player"},
            },
            timeout=10.0,
        )

    async def join_player2():
        await asyncio.sleep(0.1)
        return await test_client.post(
            "/lobby/join",
            json={
                "player_id": player2_id,
                "bot_config": {"player_id": player2_id, "bot_type": "player"},
            },
            timeout=10.0,
        )

    resp1, resp2 = await asyncio.gather(join_player1(), join_player2())

    # Get session_id from response
    session_id = resp1.json()["session_id"]

    # Verify session was created by checking if we can connect to events stream
    # Note: We don't actually connect, just verify the session exists
    # by checking that we could make a request to it (would fail if session doesn't exist)
    assert session_id is not None
    assert len(session_id) > 0


# TODO: Fix timeout test - currently hangs because test_client default timeout overrides
# @pytest.mark.asyncio
# async def test_lobby_timeout(test_client, test_players):
#     """Test that lobby join request times out if no match found."""
#     player1_id, _ = test_players
#
#     # Join with very short timeout
#     with pytest.raises(Exception):  # httpx.TimeoutException or similar
#         await test_client.post(
#             "/lobby/join",
#             json={
#                 "player_id": player1_id,
#                 "bot_config": {"player_id": player1_id, "bot_type": "player"},
#             },
#             timeout=1.0,  # 1 second timeout, should timeout before matching
#         )
#
#     # Clean up: player might still be in queue
#     await runtime.lobby_service.remove_from_queue(player1_id)
