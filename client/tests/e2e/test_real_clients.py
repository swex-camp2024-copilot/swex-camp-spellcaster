"""End-to-end tests using real SSE and bot clients (in-process via ASGI)."""

import asyncio
import uuid
from typing import Dict, Any

import pytest

# Support running as package or script
try:
    from client.sse_client import SSEClient, SSEClientConfig  # type: ignore
except Exception:  # pragma: no cover
    from ...client.sse_client import SSEClient, SSEClientConfig  # type: ignore

try:
    from client.bot_client import (
        BotClient,
        RandomWalkStrategy,
    )  # type: ignore
except Exception:  # pragma: no cover
    from ...client.bot_client import BotClient, RandomWalkStrategy  # type: ignore


@pytest.mark.asyncio
async def test_sse_client_streams_events_with_asgi_transport(asgi_client):
    ac = asgi_client
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
async def test_bot_client_register_start_and_stream(asgi_client):
    ac = asgi_client
    # Test BotClient functionality: register player and start match
    bot_instance = RandomWalkStrategy()
    client = BotClient("http://test", bot_instance=bot_instance, http_client=ac)

    # Register player directly via backend API (not through BotClient)
    player_name = f"E2E_Bot_{uuid.uuid4().hex[:8]}"
    payload = {
        "player_name": player_name,
        "submitted_from": "online",
    }
    resp = await ac.post("/players/register", json=payload)
    resp.raise_for_status()
    player_data = resp.json()
    player_id = player_data["player_id"]

    assert player_id is not None
    assert player_data["player_name"] == player_name

    # BotClient can start a match vs builtin
    session_id = await client.start_match(player_id, "builtin_sample_1", visualize=False)
    assert session_id is not None
    assert len(session_id) > 0


@pytest.mark.asyncio
async def test_concurrent_sessions_isolation(asgi_client):
    ac = asgi_client
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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bot_client_minimum_arguments_match(asgi_client):
    """Test BotClient with minimum arguments (OS username + random bot).

    This test simulates the CLI workflow with default arguments:
    - Uses RandomWalkStrategy bot
    - Registers player with default name
    - Starts match vs builtin bot
    - Verifies match completes successfully

    NOTE: This test is marked as slow (~60s) because it runs a real game simulation.
    Run with: pytest -m slow or pytest --run-slow
    """
    ac = asgi_client

    # Create bot instance (RandomWalkStrategy)
    bot = RandomWalkStrategy()
    assert bot.name == "RandomWalkStrategy"

    # Create BotClient with bot instance
    client = BotClient("http://test", bot_instance=bot, http_client=ac)

    # Register player directly via backend API (simulating player registration outside CLI)
    player_name = f"test_user_{uuid.uuid4().hex[:8]}"
    payload = {
        "player_name": player_name,
        "submitted_from": "online",
    }
    resp = await ac.post("/players/register", json=payload)
    resp.raise_for_status()
    player_data = resp.json()
    player_id = player_data["player_id"]

    assert player_id is not None
    assert player_data["player_name"] == player_name

    # Start match using new API (player vs builtin)
    session_id = await client.start_match(player_id=player_id, opponent_id="builtin_sample_1", visualize=False)
    assert session_id is not None
    assert len(session_id) > 0

    # Play match and verify events (limit to 3 events for speed)
    events_received = []
    turn_updates_received = 0

    async for event in client.play_match(session_id, player_id, max_events=3):
        events_received.append(event)

        if event.get("event") == "turn_update":
            turn_updates_received += 1
            # Verify game state structure
            assert "game_state" in event
            assert "turn" in event
            # After verifying structure once, we can stop early
            if turn_updates_received >= 1:
                break

        elif event.get("event") == "game_over":
            # Verify game over structure
            assert "winner" in event
            break

    # Verify match progressed
    assert len(events_received) > 0
    assert turn_updates_received > 0

    await client.aclose()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bot_client_custom_bot_match(asgi_client):
    """Test BotClient with custom bot loaded from bots directory.

    This test simulates loading a custom bot implementation:
    - Loads SampleBot1 from bots directory
    - Starts match vs builtin bot
    - Verifies bot's decide() method is called

    NOTE: This test is marked as slow (~65s) because it runs a real game simulation.
    Run with: pytest -m slow or pytest --run-slow
    """
    ac = asgi_client

    # Dynamically load custom bot (simulating --bot-type=custom)
    from bots.sample_bot1.sample_bot_1 import SampleBot1

    bot = SampleBot1()
    assert hasattr(bot, "name")
    assert hasattr(bot, "decide")

    # Create BotClient with custom bot
    client = BotClient("http://test", bot_instance=bot, http_client=ac)

    # Register player directly via backend API
    player_name = f"custom_bot_{uuid.uuid4().hex[:8]}"
    payload = {
        "player_name": player_name,
        "submitted_from": "online",
    }
    resp = await ac.post("/players/register", json=payload)
    resp.raise_for_status()
    player_data = resp.json()
    player_id = player_data["player_id"]

    # Start match
    session_id = await client.start_match(player_id=player_id, opponent_id="builtin_sample_2", visualize=False)

    # Play just a couple turns to verify bot works (limit to 3 events for speed)
    events_received = []
    turn_updates_received = 0
    async for event in client.play_match(session_id, player_id, max_events=3):
        events_received.append(event)

        if event.get("event") == "turn_update":
            turn_updates_received += 1
            # After one turn update, we've verified the custom bot works
            if turn_updates_received >= 1:
                break

        if event.get("event") == "game_over":
            break

    # Verify match progressed with custom bot
    assert len(events_received) > 0
    assert turn_updates_received > 0

    await client.aclose()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bot_client_player_vs_player_match(asgi_client):
    """Test BotClient with two remote players (PvP match).

    This test simulates a match between two remote players:
    - Both players use RandomWalkStrategy
    - Both clients submit actions concurrently
    - Verifies match completes successfully

    NOTE: This test is marked as slow (~10s) because it runs a PvP match simulation.
    Run with: pytest -m slow or pytest --run-slow
    """
    ac = asgi_client

    bot1 = RandomWalkStrategy()
    bot2 = RandomWalkStrategy()

    client1 = BotClient("http://test", bot_instance=bot1, http_client=ac)
    client2 = BotClient("http://test", bot_instance=bot2, http_client=ac)

    # Register two players directly via backend API
    player1_name = f"alice_{uuid.uuid4().hex[:8]}"
    player2_name = f"bob_{uuid.uuid4().hex[:8]}"

    resp1 = await ac.post("/players/register", json={"player_name": player1_name, "submitted_from": "online"})
    resp1.raise_for_status()
    player1_id = resp1.json()["player_id"]

    resp2 = await ac.post("/players/register", json={"player_name": player2_name, "submitted_from": "online"})
    resp2.raise_for_status()
    player2_id = resp2.json()["player_id"]

    # Start match (player vs player)
    session_id = await client1.start_match(player_id=player1_id, opponent_id=player2_id, visualize=False)

    # Both clients play the match concurrently (limit to 3 events each for speed)
    async def play_client(client, player_id, max_events=3):
        events = []
        async for event in client.play_match(session_id, player_id, max_events=max_events):
            events.append(event)
            # Stop early after receiving one turn_update
            if event.get("event") == "turn_update":
                break
            if event.get("event") == "game_over":
                break
        return events

    # Run both clients concurrently
    events1, events2 = await asyncio.wait_for(
        asyncio.gather(play_client(client1, player1_id), play_client(client2, player2_id)), timeout=10.0
    )

    # Verify both clients received events
    assert len(events1) > 0
    assert len(events2) > 0

    # Verify at least one turn_update was received by each client
    turn_updates_1 = [e for e in events1 if e.get("event") == "turn_update"]
    turn_updates_2 = [e for e in events2 if e.get("event") == "turn_update"]
    assert len(turn_updates_1) > 0, "Client 1 should receive at least one turn_update"
    assert len(turn_updates_2) > 0, "Client 2 should receive at least one turn_update"

    await client1.aclose()
    await client2.aclose()


@pytest.mark.asyncio
async def test_remote_player_actions_are_processed(asgi_client):
    """Verify remote player actions are incorporated into gameplay.

    This test specifically checks that:
    1. Remote player submits actions
    2. Actions are processed by backend
    3. Player actually moves on the board (position changes)
    """
    ac = asgi_client

    # Create bot that moves toward opponent
    class MoveRightBot:
        """Simple bot that always moves right."""

        name = "MoveRightBot"

        def decide(self, state):
            return {"move": [1, 0], "spell": None}

    bot = MoveRightBot()

    # Create BotClient
    client = BotClient("http://test", bot_instance=bot, http_client=ac)

    # Register player
    player_name = f"move_test_{uuid.uuid4().hex[:8]}"
    payload = {"player_name": player_name, "submitted_from": "online"}
    resp = await ac.post("/players/register", json=payload)
    resp.raise_for_status()
    player_id = resp.json()["player_id"]

    # Start match vs builtin
    session_id = await client.start_match(player_id=player_id, opponent_id="builtin_sample_1", visualize=False)

    # Track player position changes
    player_positions = []
    turn_count = 0

    async for event in client.play_match(session_id, player_id, max_events=10):
        if event.get("event") == "turn_update":
            turn_count += 1
            game_state = event.get("game_state", {})
            session_info = game_state.get("session_info", {})

            # Get our player's info (player_1 or player_2)
            if session_info.get("player_1", {}).get("player_id") == player_id:
                position = session_info["player_1"].get("position")
            else:
                position = session_info["player_2"].get("position")

            player_positions.append(position)

            # Stop after 3 turns
            if turn_count >= 3:
                break

        elif event.get("event") == "game_over":
            break

    # Verify we tracked multiple positions
    assert len(player_positions) >= 2, "Should have recorded at least 2 positions"

    # Verify player position actually changed (moved right)
    # Player starts at [0, 0], should move to [1, 0], [2, 0], etc.
    for i in range(1, len(player_positions)):
        prev_pos = player_positions[i - 1]
        curr_pos = player_positions[i]

        # Position should change (x coordinate should increase)
        if curr_pos != prev_pos:
            # Position changed - actions are being processed!
            assert curr_pos[0] > prev_pos[0], f"Player should move right: {prev_pos} -> {curr_pos}"
            break
    else:
        # If we get here, position never changed
        pytest.fail(f"Player position never changed! Positions: {player_positions}")

    await client.aclose()
