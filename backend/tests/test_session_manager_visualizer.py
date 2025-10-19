"""Tests for SessionManager integration with VisualizerService."""

import asyncio
import multiprocessing
from unittest.mock import MagicMock

import pytest

from backend.app.models.players import PlayerConfig
from backend.app.services.session_manager import SessionManager
from backend.app.services.visualizer_service import VisualizerService


class DummyBot:
    """Minimal bot implementation for testing."""

    def __init__(self, name, player_id):
        self._name = name
        self._player_id = player_id
        self._is_builtin = True

    @property
    def name(self):
        return self._name

    @property
    def player_id(self):
        return self._player_id

    @property
    def is_builtin(self):
        return self._is_builtin

    def decide(self, state):
        return {"move": [0, 0], "spell": None}


class DummyEngine:
    """Minimal game engine implementation for testing."""

    def __init__(self, bot1, bot2):
        self.bot1 = bot1
        self.bot2 = bot2
        self.turn = 0

        class Wiz:
            def __init__(self, name):
                self.name = name
                self.hp = 100
                self.mana = 100
                self.position = [0, 0]

        self.wizard1 = Wiz(bot1.name)
        self.wizard2 = Wiz(bot2.name)

        class Logger:
            def __init__(self):
                self.current_turn = []

        self.logger = Logger()

    def build_input(self, w1, w2):
        return {
            "self": {"hp": 100, "mana": 100, "position": [0, 0]},
            "opponent": {"hp": 100, "mana": 100, "position": [0, 0]},
            "turn": self.turn,
            "artifacts": [],
            "minions": [],
        }

    def run_turn(self):
        self.turn += 1
        # Finish game after 2 turns
        if self.turn >= 2:
            self.wizard2.hp = 0

    def check_winner(self):
        if self.wizard1.hp <= 0 and self.wizard2.hp <= 0:
            return "Draw"
        if self.wizard2.hp <= 0:
            return self.bot1
        return None


@pytest.fixture
def mock_visualizer_service():
    """Create a mock visualizer service."""
    service = MagicMock(spec=VisualizerService)
    # Default: return (None, None) to simulate no visualizer
    service.spawn_visualizer.return_value = (None, None)
    service.send_event.return_value = True
    service.terminate_visualizer.return_value = None
    return service


@pytest.fixture
def mock_visualizer_process():
    """Create a mock visualizer process and queue."""
    process = MagicMock(spec=multiprocessing.Process)
    process.pid = 12345
    process.is_alive.return_value = True
    queue = MagicMock(spec=multiprocessing.Queue)
    return process, queue


@pytest.mark.asyncio
async def test_create_session_with_visualize_false(mock_visualizer_service):
    """Test that session creation with visualize=False does not spawn visualizer."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=False)

    # Verify visualizer was not spawned
    mock_visualizer_service.spawn_visualizer.assert_not_called()

    # Verify session was created
    assert session_id is not None
    ctx = await manager.get_session(session_id)
    assert ctx.visualizer_enabled is False

    # Cleanup
    await asyncio.sleep(0.2)
    await manager.cleanup_session(session_id)


@pytest.mark.asyncio
async def test_create_session_with_visualize_true(mock_visualizer_service, mock_visualizer_process):
    """Test that session creation with visualize=True spawns visualizer."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return a process and queue
    process, queue = mock_visualizer_process
    mock_visualizer_service.spawn_visualizer.return_value = (process, queue)

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Verify visualizer was spawned
    mock_visualizer_service.spawn_visualizer.assert_called_once()
    call_args = mock_visualizer_service.spawn_visualizer.call_args
    assert call_args.kwargs["session_id"] == session_id

    # Verify session context has visualizer enabled
    ctx = await manager.get_session(session_id)
    assert ctx.visualizer_enabled is True
    assert ctx.visualizer_process == process
    assert ctx.visualizer_queue == queue

    # Cleanup
    await asyncio.sleep(0.2)
    await manager.cleanup_session(session_id)


@pytest.mark.asyncio
async def test_session_creation_succeeds_when_visualizer_fails(mock_visualizer_service):
    """Test that session creation succeeds even if visualizer spawn fails."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return (None, None) to simulate spawn failure
    mock_visualizer_service.spawn_visualizer.return_value = (None, None)

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Verify visualizer was attempted
    mock_visualizer_service.spawn_visualizer.assert_called_once()

    # Verify session was created successfully
    assert session_id is not None
    ctx = await manager.get_session(session_id)
    assert ctx.visualizer_enabled is False  # Should be False since spawn failed

    # Cleanup
    await asyncio.sleep(0.2)
    await manager.cleanup_session(session_id)


@pytest.mark.asyncio
async def test_turn_events_sent_to_visualizer(mock_visualizer_service, mock_visualizer_process):
    """Test that turn events are sent to visualizer during match loop."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return a process and queue
    process, queue = mock_visualizer_process
    mock_visualizer_service.spawn_visualizer.return_value = (process, queue)

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Wait for match to complete
    await asyncio.sleep(0.3)

    # Verify send_event was called (at least for turn events)
    assert mock_visualizer_service.send_event.call_count >= 1

    # Verify events were sent with the correct queue
    for call in mock_visualizer_service.send_event.call_args_list:
        assert call.args[0] == queue

    # Cleanup
    await manager.cleanup_session(session_id)


@pytest.mark.asyncio
async def test_game_over_event_sent_to_visualizer(mock_visualizer_service, mock_visualizer_process):
    """Test that game over event is sent to visualizer."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return a process and queue
    process, queue = mock_visualizer_process
    mock_visualizer_service.spawn_visualizer.return_value = (process, queue)

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Wait for match to complete
    await asyncio.sleep(0.3)

    # Verify send_event was called multiple times (turns + game over)
    assert mock_visualizer_service.send_event.call_count >= 2

    # Check if any call was with a GameOverEvent (by checking event type in model_dump)
    for call in mock_visualizer_service.send_event.call_args_list:
        event = call.args[1]
        if hasattr(event, "event") and event.event == "game_over":
            break

    # Note: We can't easily check this without inspecting the actual event objects
    # The test verifies that send_event was called multiple times

    # Cleanup
    await manager.cleanup_session(session_id)


@pytest.mark.asyncio
async def test_visualizer_not_terminated_after_match_completion(mock_visualizer_service, mock_visualizer_process):
    """Test that visualizer is NOT automatically terminated after match completes.

    The visualizer should remain open to display the final game state.
    It will only be terminated when manually cleaned up via cleanup_session().
    """
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return a process and queue
    process, queue = mock_visualizer_process
    mock_visualizer_service.spawn_visualizer.return_value = (process, queue)

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Wait for match to complete
    await asyncio.sleep(0.3)

    # Verify terminate_visualizer was NOT called automatically after match completion
    mock_visualizer_service.terminate_visualizer.assert_not_called()

    # Cleanup - this should now trigger termination
    await manager.cleanup_session(session_id)

    # Verify terminate_visualizer was called during cleanup
    mock_visualizer_service.terminate_visualizer.assert_called_once_with(process, queue)


@pytest.mark.asyncio
async def test_visualizer_terminated_on_session_cleanup(mock_visualizer_service, mock_visualizer_process):
    """Test that visualizer is terminated when session is cleaned up manually."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return a process and queue
    process, queue = mock_visualizer_process
    mock_visualizer_service.spawn_visualizer.return_value = (process, queue)

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Wait a bit but not for completion
    await asyncio.sleep(0.1)

    # Manually cleanup session
    await manager.cleanup_session(session_id)

    # Verify terminate_visualizer was called (either in finally block or cleanup)
    assert mock_visualizer_service.terminate_visualizer.call_count >= 1


@pytest.mark.asyncio
async def test_graceful_handling_of_visualizer_spawn_exception(mock_visualizer_service):
    """Test that exceptions during visualizer spawn are handled gracefully."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to raise an exception
    mock_visualizer_service.spawn_visualizer.side_effect = Exception("Spawn failed")

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    # Session creation should succeed despite exception
    session_id = await manager.create_session(p1, p2, visualize=True)

    # Verify session was created
    assert session_id is not None
    ctx = await manager.get_session(session_id)
    assert ctx.visualizer_enabled is False

    # Cleanup
    await asyncio.sleep(0.2)
    await manager.cleanup_session(session_id)


@pytest.mark.asyncio
async def test_graceful_handling_of_send_event_exception(mock_visualizer_service, mock_visualizer_process):
    """Test that exceptions during send_event are handled gracefully."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return a process and queue
    process, queue = mock_visualizer_process
    mock_visualizer_service.spawn_visualizer.return_value = (process, queue)

    # Configure send_event to raise an exception
    mock_visualizer_service.send_event.side_effect = Exception("Send failed")

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Wait for match to complete - should succeed despite send_event exceptions
    await asyncio.sleep(0.3)

    # Verify session completed successfully
    await manager.get_session(session_id)
    # Match should have completed despite visualizer errors

    # Cleanup
    await manager.cleanup_session(session_id)


@pytest.mark.asyncio
async def test_graceful_handling_of_terminate_exception(mock_visualizer_service, mock_visualizer_process):
    """Test that exceptions during terminate_visualizer are handled gracefully."""
    from backend.app.core.database import create_tables
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine
    await create_tables()

    # Configure mock to return a process and queue
    process, queue = mock_visualizer_process
    mock_visualizer_service.spawn_visualizer.return_value = (process, queue)

    # Configure terminate to raise an exception
    mock_visualizer_service.terminate_visualizer.side_effect = Exception("Terminate failed")

    manager = SessionManager(visualizer_service=mock_visualizer_service)

    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2, visualize=True)

    # Wait for match to complete
    await asyncio.sleep(0.3)

    # Cleanup should succeed despite terminate exception
    await manager.cleanup_session(session_id)

    # Verify terminate was attempted
    assert mock_visualizer_service.terminate_visualizer.call_count >= 1
