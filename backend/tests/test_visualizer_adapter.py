"""Unit tests for VisualizerAdapter."""

import queue
from unittest.mock import MagicMock, Mock, patch

import pytest

from backend.app.services.visualizer_adapter import VisualizerAdapter, run_visualizer_adapter


@pytest.fixture
def mock_queue():
    """Create a mock multiprocessing queue."""
    return MagicMock()


@pytest.fixture
def adapter(mock_queue):
    """Create a VisualizerAdapter instance for testing."""
    return VisualizerAdapter(
        session_id="test-session",
        event_queue=mock_queue,
        player1_name="Player1",
        player2_name="Player2",
        player1_sprite="assets/wizards/player1.png",
        player2_sprite="assets/wizards/player2.png",
    )


class TestVisualizerAdapterInit:
    """Tests for VisualizerAdapter initialization."""

    def test_init_stores_configuration(self, mock_queue):
        """Test that initialization stores all configuration parameters."""
        adapter = VisualizerAdapter(
            session_id="test-session",
            event_queue=mock_queue,
            player1_name="Bot1",
            player2_name="Bot2",
            player1_sprite="sprite1.png",
            player2_sprite="sprite2.png",
        )

        assert adapter._session_id == "test-session"
        assert adapter._queue == mock_queue
        assert adapter._player1_name == "Bot1"
        assert adapter._player2_name == "Bot2"
        assert adapter._player1_sprite == "sprite1.png"
        assert adapter._player2_sprite == "sprite2.png"
        assert adapter._visualizer is None
        assert adapter._states == []
        assert adapter._running is True

    def test_init_with_optional_sprites(self, mock_queue):
        """Test initialization with optional sprite parameters."""
        adapter = VisualizerAdapter(
            session_id="test-session",
            event_queue=mock_queue,
            player1_name="Bot1",
            player2_name="Bot2",
        )

        assert adapter._player1_sprite is None
        assert adapter._player2_sprite is None


class TestVisualizerAdapterInitialization:
    """Tests for visualizer initialization."""

    def test_initialize_visualizer_success(self, adapter):
        """Test successful pygame initialization."""
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            adapter.initialize_visualizer()
            # Should not raise any exceptions

    def test_initialize_visualizer_pygame_unavailable(self, adapter):
        """Test graceful handling when pygame is unavailable."""

        # Mock pygame import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == "pygame":
                raise ImportError("pygame not found")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import), pytest.raises(ImportError):
            adapter.initialize_visualizer()


class TestVisualizerAdapterEventHandling:
    """Tests for event handling methods."""

    def test_handle_turn_event_accumulates_state(self, adapter):
        """Test that turn events accumulate game states and render in real-time."""
        # Mock the visualizer
        adapter._visualizer = MagicMock()

        event = {
            "event": "turn_update",
            "turn": 1,
            "game_state": {
                "self": {"name": "Player1", "hp": 100, "mana": 50, "position": [0, 0]},
                "opponent": {"name": "Player2", "hp": 100, "mana": 50, "position": [9, 9]},
                "artifacts": [],
                "minions": [],
            },
        }

        adapter.handle_turn_event(event)

        assert len(adapter._states) == 1
        assert adapter._states[0] == event["game_state"]
        # Verify visualizer was called to render
        adapter._visualizer.render_frame.assert_called_once()

    def test_handle_turn_event_missing_game_state(self, adapter):
        """Test handling of turn event without game_state."""
        event = {"event": "turn_update", "turn": 1}

        adapter.handle_turn_event(event)

        assert len(adapter._states) == 0

    def test_handle_turn_event_multiple_turns(self, adapter):
        """Test accumulating multiple turn events with real-time rendering."""
        # Mock the visualizer
        adapter._visualizer = MagicMock()

        for i in range(5):
            event = {
                "event": "turn_update",
                "turn": i,
                "game_state": {"turn": i, "data": f"state_{i}"},
            }
            adapter.handle_turn_event(event)

        assert len(adapter._states) == 5
        assert adapter._states[0]["turn"] == 0
        assert adapter._states[4]["turn"] == 4
        # First turn renders frame, subsequent turns animate transitions
        assert adapter._visualizer.render_frame.call_count == 1
        assert adapter._visualizer.animate_transition.call_count == 4

    def test_handle_game_over_event(self, adapter):
        """Test handling of game over event with end game message."""
        # Mock the visualizer
        adapter._visualizer = MagicMock()

        # Add some existing states
        adapter._states = [{"turn": 0}, {"turn": 1}]

        event = {
            "event": "game_over",
            "final_state": {"turn": 2, "game_over": True},
            "winner_name": "Player1",
        }

        adapter.handle_game_over_event(event)

        assert len(adapter._states) == 3
        assert adapter._states[-1] == event["final_state"]
        # Verify end game message is displayed
        adapter._visualizer.display_end_game_message.assert_called_once_with("Player1", has_more_matches=False)

    def test_handle_game_over_event_without_final_state(self, adapter):
        """Test handling of game over event without final_state."""
        # Mock the visualizer
        adapter._visualizer = MagicMock()

        adapter._states = [{"turn": 0}]

        event = {"event": "game_over", "winner_name": "Player1"}

        adapter.handle_game_over_event(event)

        assert len(adapter._states) == 1
        # Verify end game message is still displayed
        adapter._visualizer.display_end_game_message.assert_called_once_with("Player1", has_more_matches=False)


class TestVisualizerAdapterProcessEvents:
    """Tests for event processing loop."""

    def test_process_events_handles_turn_update(self, adapter, mock_queue):
        """Test processing of turn_update events with real-time rendering."""
        # Mock the visualizer
        adapter._visualizer = MagicMock()

        events = [
            {
                "event": "turn_update",
                "turn": 0,
                "game_state": {"turn": 0},
            },
            {
                "event": "game_over",
                "final_state": {"turn": 1},
                "winner_name": "Player1",
            },
        ]

        mock_queue.get.side_effect = events

        adapter.process_events()

        assert len(adapter._states) == 2
        assert not adapter._running
        # Verify real-time rendering occurred
        adapter._visualizer.render_frame.assert_called_once()
        adapter._visualizer.display_end_game_message.assert_called_once()

    def test_process_events_handles_shutdown(self, adapter, mock_queue):
        """Test processing of shutdown event."""
        mock_queue.get.return_value = {"event": "shutdown"}

        adapter.process_events()

        assert not adapter._running

    def test_process_events_handles_queue_empty(self, adapter, mock_queue):
        """Test handling of empty queue (timeout)."""
        # First call raises Empty, second call returns shutdown
        mock_queue.get.side_effect = [
            queue.Empty(),
            {"event": "shutdown"},
        ]

        with patch.object(adapter, "_handle_pygame_events"):
            adapter.process_events()

        assert not adapter._running

    def test_process_events_handles_unknown_event(self, adapter, mock_queue):
        """Test handling of unknown event type."""
        mock_queue.get.side_effect = [
            {"event": "unknown_event"},
            {"event": "shutdown"},
        ]

        adapter.process_events()

        assert not adapter._running


class TestVisualizerAdapterPygameEvents:
    """Tests for pygame event handling."""

    def test_handle_pygame_events_quit(self, adapter):
        """Test handling of pygame QUIT event."""
        mock_pygame = MagicMock()
        mock_event = Mock()
        mock_event.type = mock_pygame.QUIT
        mock_pygame.event.get.return_value = [mock_event]

        with patch.dict("sys.modules", {"pygame": mock_pygame}):
            adapter._handle_pygame_events()

        assert not adapter._running

    def test_handle_pygame_events_no_quit(self, adapter):
        """Test handling of non-QUIT pygame events."""
        mock_pygame = MagicMock()
        mock_event = Mock()
        mock_event.type = 999  # Some other event type
        mock_pygame.event.get.return_value = [mock_event]

        with patch.dict("sys.modules", {"pygame": mock_pygame}):
            adapter._handle_pygame_events()

        assert adapter._running

    def test_handle_pygame_events_pygame_unavailable(self, adapter):
        """Test graceful handling when pygame is unavailable."""

        # Mock pygame import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == "pygame":
                raise ImportError("pygame not found")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            adapter._handle_pygame_events()
            # Should not raise exception


class TestVisualizerAdapterShutdown:
    """Tests for shutdown functionality."""

    def test_shutdown_success(self, adapter):
        """Test successful pygame shutdown."""
        mock_pygame = MagicMock()

        with patch.dict("sys.modules", {"pygame": mock_pygame}):
            adapter.shutdown()

        mock_pygame.quit.assert_called_once()

    def test_shutdown_pygame_unavailable(self, adapter):
        """Test shutdown when pygame is unavailable."""

        # Mock pygame import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == "pygame":
                raise ImportError("pygame not found")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            adapter.shutdown()
            # Should not raise exception

    def test_shutdown_handles_errors(self, adapter):
        """Test shutdown handles pygame errors gracefully."""
        mock_pygame = MagicMock()
        mock_pygame.quit.side_effect = Exception("Shutdown error")

        with patch.dict("sys.modules", {"pygame": mock_pygame}):
            adapter.shutdown()
            # Should not raise exception


class TestRunVisualizerAdapter:
    """Tests for run_visualizer_adapter entry point."""

    @patch("backend.app.services.visualizer_adapter.VisualizerAdapter")
    def test_run_visualizer_adapter_success(self, mock_adapter_class):
        """Test successful execution of visualizer adapter."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter
        mock_queue = MagicMock()

        run_visualizer_adapter(
            session_id="test-session",
            event_queue=mock_queue,
            player1_name="Bot1",
            player2_name="Bot2",
            player1_sprite="sprite1.png",
            player2_sprite="sprite2.png",
        )

        mock_adapter_class.assert_called_once_with(
            session_id="test-session",
            event_queue=mock_queue,
            player1_name="Bot1",
            player2_name="Bot2",
            player1_sprite="sprite1.png",
            player2_sprite="sprite2.png",
        )
        mock_adapter.initialize_visualizer.assert_called_once()
        mock_adapter.process_events.assert_called_once()
        mock_adapter.shutdown.assert_called_once()

    @patch("backend.app.services.visualizer_adapter.VisualizerAdapter")
    def test_run_visualizer_adapter_initialization_error(self, mock_adapter_class):
        """Test handling of initialization errors."""
        mock_adapter = MagicMock()
        mock_adapter.initialize_visualizer.side_effect = Exception("Init error")
        mock_adapter_class.return_value = mock_adapter
        mock_queue = MagicMock()

        with pytest.raises(SystemExit):
            run_visualizer_adapter(
                session_id="test-session",
                event_queue=mock_queue,
                player1_name="Bot1",
                player2_name="Bot2",
            )

    @patch("backend.app.services.visualizer_adapter.VisualizerAdapter")
    def test_run_visualizer_adapter_with_optional_sprites(self, mock_adapter_class):
        """Test running adapter with optional sprite parameters."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter
        mock_queue = MagicMock()

        run_visualizer_adapter(
            session_id="test-session",
            event_queue=mock_queue,
            player1_name="Bot1",
            player2_name="Bot2",
        )

        mock_adapter_class.assert_called_once_with(
            session_id="test-session",
            event_queue=mock_queue,
            player1_name="Bot1",
            player2_name="Bot2",
            player1_sprite=None,
            player2_sprite=None,
        )
