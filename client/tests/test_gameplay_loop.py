"""Unit tests for BotClient gameplay loop (Task 3.5)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from client.bot_client import BotClient, RandomWalkStrategy


class MockBot:
    """Mock bot for testing that implements BotInterface."""

    def __init__(self, action_sequence: list[Dict[str, Any]] | None = None):
        """Initialize mock bot with optional sequence of actions to return.

        Args:
            action_sequence: List of actions to return in sequence. If None, returns default action.
        """
        self._action_sequence = action_sequence or []
        self._action_index = 0

    @property
    def name(self) -> str:
        return "MockBot"

    def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Return next action from sequence or default action."""
        if self._action_index < len(self._action_sequence):
            action = self._action_sequence[self._action_index]
            self._action_index += 1
            return action
        return {"move": [0, 0], "spell": None}


@pytest.mark.asyncio
async def test_play_match_with_random_walk_strategy():
    """Test play_match with RandomWalkStrategy bot instance."""
    bot = RandomWalkStrategy()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Mock session events
    events = [
        {"event": "session_start", "session_id": "test-session"},
        {
            "event": "turn_update",
            "turn": 0,
            "game_state": {
                "turn": 0,
                "board_size": 15,
                "self": {"position": [0, 0], "hp": 100, "mana": 100},
                "opponent": {"position": [14, 14], "hp": 100, "mana": 100},
            },
        },
        {"event": "game_over", "winner": "player1"},
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Track submit_action calls
    submitted_actions = []

    async def mock_submit(session_id, player_id, turn, action):
        submitted_actions.append({"turn": turn, "action": action})

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with (
        patch.object(client, "stream_session_events", side_effect=mock_stream),
        patch.object(client, "submit_action", side_effect=mock_submit),
    ):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify all events were yielded
    assert len(collected_events) == 3
    assert collected_events[0]["event"] == "session_start"
    assert collected_events[1]["event"] == "turn_update"
    assert collected_events[2]["event"] == "game_over"

    # Verify submit_action was called once for turn 1
    assert len(submitted_actions) == 1
    assert submitted_actions[0]["turn"] == 1
    assert submitted_actions[0]["action"]["move"] is not None  # RandomWalk returns a move


@pytest.mark.asyncio
async def test_play_match_with_custom_bot():
    """Test play_match with mock custom bot implementing BotInterface."""
    # Create mock bot with predefined actions
    actions = [
        {"move": [1, 0], "spell": None},
        {"move": [0, 1], "spell": {"name": "fireball", "target": [5, 5]}},
    ]
    bot = MockBot(action_sequence=actions)
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Mock session events with multiple turns
    events = [
        {"event": "session_start", "session_id": "test-session"},
        {
            "event": "turn_update",
            "turn": 0,
            "game_state": {
                "turn": 0,
                "self": {"position": [0, 0]},
                "opponent": {"position": [5, 5]},
            },
        },
        {
            "event": "turn_update",
            "turn": 1,
            "game_state": {
                "turn": 1,
                "self": {"position": [1, 0]},
                "opponent": {"position": [5, 5]},
            },
        },
        {"event": "game_over", "winner": "player1"},
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Mock submit_action to succeed
    mock_client.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"status": "accepted"}))

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with patch.object(client, "stream_session_events", side_effect=mock_stream):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify bot.decide() was called with correct game state
    assert bot._action_index == 2  # Both actions were used

    # Verify submit_action was called twice (for turns 1 and 2)
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_play_match_bot_decide_exception():
    """Test that bot decision exceptions are caught and match continues."""

    class ErrorBot:
        @property
        def name(self) -> str:
            return "ErrorBot"

        def decide(self, state: Dict[str, Any]) -> Dict[str, Any]:
            raise ValueError("Bot decision error")

    bot = ErrorBot()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    events = [
        {"event": "session_start", "session_id": "test-session"},
        {
            "event": "turn_update",
            "turn": 0,
            "game_state": {"turn": 0, "self": {}, "opponent": {}},
        },
        {"event": "game_over", "winner": "opponent"},
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with patch.object(client, "stream_session_events", side_effect=mock_stream):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify match continued despite bot error
    assert len(collected_events) == 3
    assert collected_events[2]["event"] == "game_over"

    # Verify submit_action was NOT called due to bot error
    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_play_match_action_submission_with_correct_payload():
    """Test that actions are submitted with correct payload structure."""
    bot = MockBot(action_sequence=[{"move": [1, 1], "spell": {"name": "shield"}}])
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    events = [
        {
            "event": "turn_update",
            "turn": 5,
            "game_state": {"turn": 5, "self": {}, "opponent": {}},
        },
        {"event": "game_over", "winner": "player1"},
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Mock submit_action to capture calls
    submitted_actions = []

    async def mock_submit(session_id, player_id, turn, action):
        submitted_actions.append({"session_id": session_id, "player_id": player_id, "turn": turn, "action": action})

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with (
        patch.object(client, "stream_session_events", side_effect=mock_stream),
        patch.object(client, "submit_action", side_effect=mock_submit),
    ):
        async for _ in client.play_match("test-session", "player1"):
            pass

    # Verify action was submitted with correct turn number (current + 1)
    assert len(submitted_actions) == 1
    assert submitted_actions[0]["turn"] == 6  # turn 5 + 1
    assert submitted_actions[0]["action"]["move"] == [1, 1]
    assert submitted_actions[0]["action"]["spell"]["name"] == "shield"


@pytest.mark.asyncio
async def test_play_match_stops_on_game_over():
    """Test that play_match stops processing after game_over event."""
    bot = RandomWalkStrategy()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Events after game_over should not be processed
    events = [
        {"event": "session_start"},
        {"event": "game_over", "winner": "player1"},
        {"event": "turn_update", "turn": 100},  # This should not be processed
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with patch.object(client, "stream_session_events", side_effect=mock_stream):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify only events up to game_over were processed
    assert len(collected_events) == 2
    assert collected_events[0]["event"] == "session_start"
    assert collected_events[1]["event"] == "game_over"


@pytest.mark.asyncio
async def test_play_match_action_submission_http_error():
    """Test that HTTP errors during action submission are logged and match continues."""
    bot = RandomWalkStrategy()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    events = [
        {
            "event": "turn_update",
            "turn": 0,
            "game_state": {"turn": 0, "self": {}, "opponent": {}},
        },
        {
            "event": "turn_update",
            "turn": 1,
            "game_state": {"turn": 1, "self": {}, "opponent": {}},
        },
        {"event": "game_over", "winner": "opponent"},
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Mock submit_action to raise HTTP error on first call, succeed on second
    call_count = 0

    async def mock_submit(session_id, player_id, turn, action):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.HTTPStatusError(
                "Bad request",
                request=MagicMock(),
                response=MagicMock(status_code=400, text="Invalid turn"),
            )

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with (
        patch.object(client, "stream_session_events", side_effect=mock_stream),
        patch.object(client, "submit_action", side_effect=mock_submit),
    ):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify match continued despite HTTP error
    assert len(collected_events) == 3
    assert call_count == 2  # submit_action was called twice


@pytest.mark.asyncio
async def test_match_termination_game_over_logs_winner():
    """Test that game_over event logs winner information (Task 4.5)."""
    bot = RandomWalkStrategy()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    events = [
        {"event": "session_start"},
        {"event": "game_over", "winner": "player1"},
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with (
        patch.object(client, "stream_session_events", side_effect=mock_stream),
        patch("client.bot_client.logger") as mock_logger,
    ):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify winner was logged
    mock_logger.info.assert_any_call("Game over! Winner: player1")


@pytest.mark.asyncio
async def test_match_termination_game_over_logs_draw():
    """Test that game_over event logs draw when no winner (Task 4.5)."""
    bot = RandomWalkStrategy()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    events = [
        {"event": "session_start"},
        {"event": "game_over", "winner": None},
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with (
        patch.object(client, "stream_session_events", side_effect=mock_stream),
        patch("client.bot_client.logger") as mock_logger,
    ):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify draw was logged
    mock_logger.info.assert_any_call("Game over! Result: Draw")


@pytest.mark.asyncio
async def test_match_termination_no_events_after_game_over():
    """Test that no events are processed after game_over (Task 4.5)."""
    bot = RandomWalkStrategy()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # Events after game_over should be ignored
    events = [
        {"event": "session_start"},
        {"event": "turn_update", "turn": 1, "game_state": {"turn": 1}},
        {"event": "game_over", "winner": "player1"},
        {"event": "turn_update", "turn": 2, "game_state": {"turn": 2}},  # Should not be yielded
        {"event": "heartbeat"},  # Should not be yielded
    ]

    client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

    # Track action submissions
    submitted_actions = []

    async def mock_submit(session_id, player_id, turn, action):
        submitted_actions.append({"turn": turn})

    # Mock stream_session_events
    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    with (
        patch.object(client, "stream_session_events", side_effect=mock_stream),
        patch.object(client, "submit_action", side_effect=mock_submit),
    ):
        collected_events = []
        async for event in client.play_match("test-session", "player1"):
            collected_events.append(event)

    # Verify only events up to and including game_over were yielded
    assert len(collected_events) == 3
    assert collected_events[0]["event"] == "session_start"
    assert collected_events[1]["event"] == "turn_update"
    assert collected_events[2]["event"] == "game_over"

    # Verify only one action was submitted (for turn 1)
    assert len(submitted_actions) == 1
    assert submitted_actions[0]["turn"] == 2  # turn 1 + 1
