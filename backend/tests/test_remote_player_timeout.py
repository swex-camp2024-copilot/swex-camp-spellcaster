"""Integration tests for remote player action timeout handling (Task 3.6)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import create_tables


@pytest.mark.asyncio
async def test_remote_player_action_timeout_uses_default(test_client: AsyncClient):
    """Test that backend uses default action when remote player times out.

    Requirements: 10.2, 10.6, 5.8
    """
    await create_tables()

    # Create two players
    resp = await test_client.post("/players/register", json={"player_name": "Remote Player 1"})
    assert resp.status_code == 201
    player1_id = resp.json()["player_id"]

    resp = await test_client.post("/players/register", json={"player_name": "Remote Player 2"})
    assert resp.status_code == 201
    player2_id = resp.json()["player_id"]

    # Start a match between two remote players (both will timeout initially)
    resp = await test_client.post(
        "/playground/start",
        json={
            "player_1_config": {"player_id": player1_id, "bot_type": "player"},
            "player_2_config": {"player_id": player2_id, "bot_type": "player"},
            "visualize": False,
        },
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Wait for session_start event
    events = []
    async with test_client.stream("GET", f"/playground/{session_id}/events") as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                import json

                event = json.loads(line[5:])
                events.append(event)

                if event.get("event") == "session_start":
                    # Session started, now wait a bit for turn_update
                    await asyncio.sleep(0.1)
                    break

    # Wait for turn_update event (should have default actions since both players timed out)
    async with test_client.stream("GET", f"/playground/{session_id}/events") as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                import json

                event = json.loads(line[5:])
                events.append(event)

                if event.get("event") == "turn_update":
                    # Verify default actions were used
                    turn_event = event
                    actions = turn_event.get("actions", [])
                    assert len(actions) == 2

                    # Both players should have default move [0, 0]
                    for action in actions:
                        # Default action is move=[0,0], spell=None (from turn_processor.py:93)
                        assert action["move"] == [0, 0] or action["move"] is None
                        assert action["spell"] is None

                    break

                # Stop if we get too many events
                if len(events) > 10:
                    break


@pytest.mark.asyncio
async def test_remote_player_action_timeout_with_one_submission(test_client: AsyncClient):
    """Test that backend uses default for timed-out player while accepting other player's action.

    Requirements: 10.2, 10.4, 10.6
    """
    await create_tables()

    # Create two players
    resp = await test_client.post("/players/register", json={"player_name": "Active Player"})
    assert resp.status_code == 201
    active_player_id = resp.json()["player_id"]

    resp = await test_client.post("/players/register", json={"player_name": "Timeout Player"})
    assert resp.status_code == 201
    timeout_player_id = resp.json()["player_id"]

    # Start a match
    resp = await test_client.post(
        "/playground/start",
        json={
            "player_1_config": {"player_id": active_player_id, "bot_type": "player"},
            "player_2_config": {"player_id": timeout_player_id, "bot_type": "player"},
            "visualize": False,
        },
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Wait for session_start
    events = []
    async with test_client.stream("GET", f"/playground/{session_id}/events") as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                import json

                event = json.loads(line[5:])
                events.append(event)

                if event.get("event") == "session_start":
                    await asyncio.sleep(0.1)
                    break

    # Submit action for active player only
    resp = await test_client.post(
        f"/playground/{session_id}/action",
        json={
            "player_id": active_player_id,
            "turn": 1,
            "action_data": {"move": [1, 0], "spell": None},
        },
    )
    assert resp.status_code == 200

    # Wait for turn_update (should have active player's action + default for timeout player)
    async with test_client.stream("GET", f"/playground/{session_id}/events") as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                import json

                event = json.loads(line[5:])

                if event.get("event") == "turn_update":
                    actions = event.get("actions", [])
                    assert len(actions) == 2

                    # Find actions by player_id
                    active_action = next((a for a in actions if a["player_id"] == active_player_id), None)
                    timeout_action = next((a for a in actions if a["player_id"] == timeout_player_id), None)

                    assert active_action is not None
                    assert timeout_action is not None

                    # Active player's action should be submitted value
                    assert active_action["move"] == [1, 0]

                    # Timeout player should have default action
                    assert timeout_action["move"] == [0, 0] or timeout_action["move"] is None

                    break

                if len(events) > 10:
                    break


@pytest.mark.asyncio
async def test_remote_player_both_submit_before_timeout(test_client: AsyncClient):
    """Test that backend processes turn immediately when both players submit before timeout.

    Requirements: 10.4
    """
    await create_tables()

    # Create two players
    resp = await test_client.post("/players/register", json={"player_name": "Player 1"})
    assert resp.status_code == 201
    player1_id = resp.json()["player_id"]

    resp = await test_client.post("/players/register", json={"player_name": "Player 2"})
    assert resp.status_code == 201
    player2_id = resp.json()["player_id"]

    # Start a match
    resp = await test_client.post(
        "/playground/start",
        json={
            "player_1_config": {"player_id": player1_id, "bot_type": "player"},
            "player_2_config": {"player_id": player2_id, "bot_type": "player"},
            "visualize": False,
        },
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Wait for session_start
    async with test_client.stream("GET", f"/playground/{session_id}/events") as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                import json

                event = json.loads(line[5:])

                if event.get("event") == "session_start":
                    await asyncio.sleep(0.1)
                    break

    # Submit actions for both players quickly
    import time

    start_time = time.time()

    resp1 = await test_client.post(
        f"/playground/{session_id}/action",
        json={
            "player_id": player1_id,
            "turn": 1,
            "action_data": {"move": [1, 0], "spell": None},
        },
    )
    assert resp1.status_code == 200

    resp2 = await test_client.post(
        f"/playground/{session_id}/action",
        json={
            "player_id": player2_id,
            "turn": 1,
            "action_data": {"move": [0, 1], "spell": None},
        },
    )
    assert resp2.status_code == 200

    # Wait for turn_update and measure time
    async with test_client.stream("GET", f"/playground/{session_id}/events") as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                import json

                event = json.loads(line[5:])

                if event.get("event") == "turn_update":
                    elapsed = time.time() - start_time
                    actions = event.get("actions", [])

                    # Verify both actions were processed
                    assert len(actions) == 2
                    player1_action = next((a for a in actions if a["player_id"] == player1_id), None)
                    player2_action = next((a for a in actions if a["player_id"] == player2_id), None)

                    assert player1_action["move"] == [1, 0]
                    assert player2_action["move"] == [0, 1]

                    # Turn should process quickly (much less than timeout default of 5s)
                    # Allow some margin for CI/slow systems, but should be < 1s
                    assert elapsed < 2.0, f"Turn took {elapsed}s, expected < 2s when both actions submitted"

                    break
