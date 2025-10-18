"""Unit tests for VisualizerService."""

import multiprocessing
from unittest.mock import MagicMock, Mock, patch

import pytest

from backend.app.models.events import GameOverEvent, TurnEvent
from backend.app.services.visualizer_service import VisualizerService


class TestVisualizerService:
    """Test VisualizerService functionality."""

    @pytest.fixture
    def service(self):
        """Create a VisualizerService instance for testing."""
        return VisualizerService()

    def test_init(self, service):
        """Test service initialization."""
        assert service is not None
        assert service._logger is not None

    def test_is_visualization_available_with_pygame(self, service):
        """Test visualization availability when pygame is installed."""
        with patch("backend.app.services.visualizer_service.settings") as mock_settings:
            mock_settings.enable_visualization = True

            # Mock pygame import to succeed
            with patch.dict("sys.modules", {"pygame": MagicMock()}):
                assert service.is_visualization_available() is True

    def test_is_visualization_available_without_pygame(self, service):
        """Test visualization availability when pygame is not installed."""
        with patch("backend.app.services.visualizer_service.settings") as mock_settings:
            mock_settings.enable_visualization = True

            # Mock pygame import to fail
            with patch("builtins.__import__", side_effect=ImportError("No module named 'pygame'")):
                assert service.is_visualization_available() is False

    def test_is_visualization_available_disabled_in_config(self, service):
        """Test visualization availability when disabled in config."""
        with patch("backend.app.services.visualizer_service.settings") as mock_settings:
            mock_settings.enable_visualization = False

            # Even with pygame available, should return False
            with patch.dict("sys.modules", {"pygame": MagicMock()}):
                assert service.is_visualization_available() is False

    @patch("backend.app.services.visualizer_service.multiprocessing.Process")
    @patch("backend.app.services.visualizer_service.multiprocessing.Queue")
    def test_spawn_visualizer_success(self, mock_queue_class, mock_process_class, service):
        """Test successful visualizer spawn."""
        # Mock settings
        with patch("backend.app.services.visualizer_service.settings") as mock_settings:
            mock_settings.enable_visualization = True
            mock_settings.visualizer_queue_size = 100

            # Mock pygame availability
            with patch.object(service, "is_visualization_available", return_value=True):
                # Mock queue and process
                mock_queue = MagicMock()
                mock_queue_class.return_value = mock_queue

                mock_process = MagicMock()
                mock_process.pid = 12345
                mock_process_class.return_value = mock_process

                # Spawn visualizer
                process, queue = service.spawn_visualizer(
                    session_id="test-session",
                    player1_name="Player1",
                    player2_name="Player2",
                    player1_sprite="sprite1.png",
                    player2_sprite="sprite2.png",
                )

                # Verify results
                assert process == mock_process
                assert queue == mock_queue

                # Verify process was started
                mock_process.start.assert_called_once()

                # Verify queue was created with correct size
                mock_queue_class.assert_called_once_with(maxsize=100)

    def test_spawn_visualizer_pygame_unavailable(self, service):
        """Test visualizer spawn when pygame is unavailable."""
        with patch.object(service, "is_visualization_available", return_value=False):
            process, queue = service.spawn_visualizer(
                session_id="test-session", player1_name="Player1", player2_name="Player2"
            )

            # Should return (None, None)
            assert process is None
            assert queue is None

    @patch("backend.app.services.visualizer_service.multiprocessing.Process")
    @patch("backend.app.services.visualizer_service.multiprocessing.Queue")
    def test_spawn_visualizer_exception_handling(self, mock_queue_class, mock_process_class, service):
        """Test visualizer spawn handles exceptions gracefully."""
        with patch.object(service, "is_visualization_available", return_value=True):
            # Make Process raise an exception
            mock_process_class.side_effect = Exception("Process creation failed")

            process, queue = service.spawn_visualizer(
                session_id="test-session", player1_name="Player1", player2_name="Player2"
            )

            # Should return (None, None) without raising exception
            assert process is None
            assert queue is None

    def test_send_event_success(self, service):
        """Test successful event send."""
        mock_queue = MagicMock()
        event = TurnEvent(
            turn=1, game_state={"test": "state"}, actions=[], events=[], log_line="Test log"
        )

        result = service.send_event(mock_queue, event)

        assert result is True
        mock_queue.put_nowait.assert_called_once()

        # Verify event was serialized
        call_args = mock_queue.put_nowait.call_args[0][0]
        assert isinstance(call_args, dict)
        assert call_args["event"] == "turn_update"
        assert call_args["turn"] == 1

    def test_send_event_queue_full(self, service):
        """Test event send when queue is full."""
        mock_queue = MagicMock()
        mock_queue.put_nowait.side_effect = Exception("Queue full")

        event = TurnEvent(
            turn=1, game_state={"test": "state"}, actions=[], events=[], log_line="Test log"
        )

        result = service.send_event(mock_queue, event)

        # Should return False without raising exception
        assert result is False

    def test_send_event_with_game_over(self, service):
        """Test sending game over event."""
        mock_queue = MagicMock()
        event = GameOverEvent(
            winner="player1",
            winner_name="Player 1",
            final_state={"test": "state"},
            game_result={"result": "win"},
        )

        result = service.send_event(mock_queue, event)

        assert result is True
        mock_queue.put_nowait.assert_called_once()

        # Verify event was serialized
        call_args = mock_queue.put_nowait.call_args[0][0]
        assert isinstance(call_args, dict)
        assert call_args["event"] == "game_over"
        assert call_args["winner"] == "player1"

    def test_terminate_visualizer_graceful(self, service):
        """Test graceful visualizer termination."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.is_alive.return_value = False  # Process exits cleanly

        mock_queue = MagicMock()

        service.terminate_visualizer(mock_process, mock_queue, timeout=1.0)

        # Verify shutdown signal was sent
        mock_queue.put_nowait.assert_called_once()
        shutdown_event = mock_queue.put_nowait.call_args[0][0]
        assert shutdown_event["event"] == "shutdown"

        # Verify graceful join was attempted
        mock_process.join.assert_called()

        # Verify queue was closed
        mock_queue.close.assert_called_once()

    def test_terminate_visualizer_force_kill(self, service):
        """Test force termination when process doesn't exit gracefully."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.is_alive.side_effect = [True, True, False]  # Alive after join, alive after terminate, dead after kill

        mock_queue = MagicMock()

        service.terminate_visualizer(mock_process, mock_queue, timeout=0.1)

        # Verify terminate was called
        mock_process.terminate.assert_called_once()

        # Verify kill was called
        mock_process.kill.assert_called_once()

    def test_terminate_visualizer_none_process(self, service):
        """Test terminating None process (should handle gracefully)."""
        # Should not raise exception
        service.terminate_visualizer(None, None)

    def test_terminate_visualizer_without_queue(self, service):
        """Test terminating visualizer without queue."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.is_alive.return_value = False

        # Should handle None queue gracefully
        service.terminate_visualizer(mock_process, None, timeout=1.0)

        # Verify process was still terminated
        mock_process.join.assert_called()

    def test_terminate_visualizer_exception_handling(self, service):
        """Test terminate handles exceptions gracefully."""
        mock_process = MagicMock()
        mock_process.join.side_effect = Exception("Join failed")

        # Should not raise exception
        service.terminate_visualizer(mock_process, None)

    def test_visualizer_process_main_placeholder(self):
        """Test visualizer process main entry point (placeholder for Task 3)."""
        # This is a placeholder test - full implementation will be in Task 3
        # For now, just verify the method exists and can be called
        mock_queue = MagicMock()

        # The method should exit cleanly without errors
        try:
            VisualizerService._visualizer_process_main(
                session_id="test-session",
                event_queue=mock_queue,
                player1_name="Player1",
                player2_name="Player2",
                player1_sprite=None,
                player2_sprite=None,
            )
        except SystemExit:
            # Process may exit with sys.exit() which is expected
            pass


class TestVisualizerServiceIntegration:
    """Integration tests for VisualizerService."""

    @pytest.fixture
    def service(self):
        """Create a VisualizerService instance for testing."""
        return VisualizerService()

    def test_full_lifecycle_with_mocked_process(self, service):
        """Test full lifecycle: spawn, send events, terminate."""
        with patch("backend.app.services.visualizer_service.multiprocessing.Process") as mock_process_class:
            with patch("backend.app.services.visualizer_service.multiprocessing.Queue") as mock_queue_class:
                with patch.object(service, "is_visualization_available", return_value=True):
                    # Mock queue and process
                    mock_queue = MagicMock()
                    mock_queue_class.return_value = mock_queue

                    mock_process = MagicMock()
                    mock_process.pid = 12345
                    mock_process.is_alive.return_value = False
                    mock_process_class.return_value = mock_process

                    # Spawn
                    process, queue = service.spawn_visualizer(
                        session_id="test-session", player1_name="Player1", player2_name="Player2"
                    )

                    assert process is not None
                    assert queue is not None

                    # Send event
                    event = TurnEvent(
                        turn=1, game_state={"test": "state"}, actions=[], events=[], log_line="Test"
                    )
                    result = service.send_event(queue, event)
                    assert result is True

                    # Terminate
                    service.terminate_visualizer(process, queue)

                    # Verify cleanup
                    mock_process.join.assert_called()
                    mock_queue.close.assert_called()

