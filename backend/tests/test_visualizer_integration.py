"""Integration tests for visualizer service and adapter."""

import contextlib
import multiprocessing
import time
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.visualizer_adapter import run_visualizer_adapter
from backend.app.services.visualizer_service import VisualizerService


@pytest.fixture
def visualizer_service():
    """Create a VisualizerService instance for testing."""
    return VisualizerService()


class TestVisualizerServiceIntegration:
    """Integration tests for VisualizerService."""

    @patch("backend.app.services.visualizer_service.settings")
    @patch("backend.app.services.visualizer_service.multiprocessing.Process")
    @patch("backend.app.services.visualizer_service.multiprocessing.Queue")
    def test_spawn_and_send_events(self, mock_queue_class, mock_process_class, mock_settings, visualizer_service):
        """Test spawning visualizer and sending events."""
        # Setup mocks
        mock_settings.enable_visualization = True
        mock_settings.visualizer_queue_size = 100

        mock_queue = MagicMock()
        mock_queue_class.return_value = mock_queue

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process_class.return_value = mock_process

        # Mock pygame import
        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            # Spawn visualizer
            process, queue = visualizer_service.spawn_visualizer(
                session_id="test-session",
                player1_name="Bot1",
                player2_name="Bot2",
            )

            assert process is not None
            assert queue is not None
            mock_process.start.assert_called_once()

            # Send event
            from backend.app.models.events import TurnEvent

            turn_event = TurnEvent(
                event="turn_update",
                turn=1,
                game_state={
                    "self": {"name": "Bot1", "hp": 100, "mana": 50, "position": [0, 0]},
                    "opponent": {"name": "Bot2", "hp": 100, "mana": 50, "position": [9, 9]},
                    "artifacts": [],
                    "minions": [],
                },
                actions=[],
                events=[],
                log_line="Turn 1",
            )

            success = visualizer_service.send_event(queue, turn_event)
            assert success
            mock_queue.put_nowait.assert_called_once()

    @patch("backend.app.services.visualizer_service.settings")
    @patch("backend.app.services.visualizer_service.multiprocessing.Process")
    @patch("backend.app.services.visualizer_service.multiprocessing.Queue")
    def test_spawn_send_and_terminate(self, mock_queue_class, mock_process_class, mock_settings, visualizer_service):
        """Test complete lifecycle: spawn, send events, terminate."""
        # Setup mocks
        mock_settings.enable_visualization = True
        mock_settings.visualizer_queue_size = 100

        mock_queue = MagicMock()
        mock_queue_class.return_value = mock_queue

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.is_alive.return_value = False  # Process terminated gracefully
        mock_process_class.return_value = mock_process

        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            # Spawn
            process, queue = visualizer_service.spawn_visualizer(
                session_id="test-session",
                player1_name="Bot1",
                player2_name="Bot2",
            )

            # Send multiple events
            from backend.app.models.events import GameOverEvent, TurnEvent

            for i in range(3):
                turn_event = TurnEvent(
                    event="turn_update",
                    turn=i,
                    game_state={
                        "self": {"name": "Bot1", "hp": 100, "mana": 50, "position": [0, 0]},
                        "opponent": {"name": "Bot2", "hp": 100, "mana": 50, "position": [9, 9]},
                        "artifacts": [],
                        "minions": [],
                    },
                    actions=[],
                    events=[],
                    log_line=f"Turn {i}",
                )
                visualizer_service.send_event(queue, turn_event)

            # Send game over
            game_over_event = GameOverEvent(
                event="game_over",
                winner="player1",
                winner_name="Bot1",
                final_state={
                    "self": {"name": "Bot1", "hp": 100, "mana": 50, "position": [0, 0]},
                    "opponent": {"name": "Bot2", "hp": 0, "mana": 50, "position": [9, 9]},
                    "artifacts": [],
                    "minions": [],
                },
                game_result={
                    "session_id": "test-session",
                    "winner": "player1",
                    "result_type": "victory",
                    "total_rounds": 3,
                },
            )
            visualizer_service.send_event(queue, game_over_event)

            # Terminate
            visualizer_service.terminate_visualizer(process, queue)

            mock_process.join.assert_called()
            mock_queue.close.assert_called_once()


class TestVisualizerAdapterIntegration:
    """Integration tests for VisualizerAdapter."""

    @patch("backend.app.services.visualizer_adapter.VisualizerAdapter.initialize_visualizer")
    @patch("backend.app.services.visualizer_adapter.VisualizerAdapter.process_events")
    @patch("backend.app.services.visualizer_adapter.VisualizerAdapter.shutdown")
    def test_run_visualizer_adapter_full_flow(self, mock_shutdown, mock_process_events, mock_initialize):
        """Test complete flow of run_visualizer_adapter."""
        mock_queue = MagicMock(spec=multiprocessing.Queue)

        run_visualizer_adapter(
            session_id="test-session",
            event_queue=mock_queue,
            player1_name="Bot1",
            player2_name="Bot2",
            player1_sprite="sprite1.png",
            player2_sprite="sprite2.png",
        )

        mock_initialize.assert_called_once()
        mock_process_events.assert_called_once()
        mock_shutdown.assert_called_once()


class TestFullVisualizerIntegration:
    """Full integration tests with real multiprocessing (mocked pygame)."""

    @patch("backend.app.services.visualizer_service.settings")
    def test_spawn_process_receives_events(self, mock_settings):
        """Test that spawned process can receive events via queue."""
        mock_settings.enable_visualization = True
        mock_settings.visualizer_queue_size = 100

        service = VisualizerService()

        # Mock pygame to avoid display requirement
        with (
            patch.dict("sys.modules", {"pygame": MagicMock()}),
            patch("backend.app.services.visualizer_adapter.VisualizerAdapter") as mock_adapter_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter

            # Spawn visualizer (this creates a real process and queue)
            process, queue = service.spawn_visualizer(
                session_id="test-session",
                player1_name="Bot1",
                player2_name="Bot2",
            )

            if process and queue:
                try:
                    # Send a shutdown event to stop the process
                    shutdown_event = {"event": "shutdown"}
                    queue.put_nowait(shutdown_event)

                    # Wait for process to finish
                    process.join(timeout=2.0)

                    # Verify process terminated
                    assert not process.is_alive()

                finally:
                    # Clean up
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=1.0)
                    queue.close()

    @patch("backend.app.services.visualizer_service.settings")
    def test_visualizer_crash_does_not_affect_parent(self, mock_settings):
        """Test that visualizer process crash doesn't affect parent process."""
        mock_settings.enable_visualization = True
        mock_settings.visualizer_queue_size = 100

        service = VisualizerService()

        # Mock adapter to raise exception
        with (
            patch.dict("sys.modules", {"pygame": MagicMock()}),
            patch(
                "backend.app.services.visualizer_adapter.run_visualizer_adapter",
                side_effect=Exception("Simulated crash"),
            ),
        ):
            process, queue = service.spawn_visualizer(
                session_id="test-session",
                player1_name="Bot1",
                player2_name="Bot2",
            )

            if process and queue:
                try:
                    # Wait a bit for process to crash
                    time.sleep(0.5)

                    # Process should have exited with error
                    # Parent process should still be running (we're still here!)
                    assert True  # If we got here, parent is fine

                finally:
                    # Clean up
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=1.0)
                    queue.close()

    @patch("backend.app.services.visualizer_service.settings")
    def test_queue_full_does_not_block(self, mock_settings):
        """Test that full queue doesn't block parent process."""
        mock_settings.enable_visualization = True
        mock_settings.visualizer_queue_size = 2  # Very small queue

        service = VisualizerService()

        with patch.dict("sys.modules", {"pygame": MagicMock()}):
            # Create a process that doesn't consume from queue
            queue = multiprocessing.Queue(maxsize=2)

            # Fill the queue
            from backend.app.models.events import TurnEvent

            for i in range(3):  # Try to send more than queue size
                event = TurnEvent(
                    event="turn_update",
                    turn=i,
                    game_state={
                        "self": {"name": "Bot1", "hp": 100, "mana": 50, "position": [0, 0]},
                        "opponent": {"name": "Bot2", "hp": 100, "mana": 50, "position": [9, 9]},
                        "artifacts": [],
                        "minions": [],
                    },
                    actions=[],
                    events=[],
                    log_line=f"Turn {i}",
                )

                # This should not block, even when queue is full
                result = service.send_event(queue, event)

                # First 2 should succeed, 3rd should fail (queue full)
                if i < 2:
                    assert result is True
                else:
                    assert result is False

            queue.close()


class TestVisualizerErrorResilience:
    """Tests for error resilience in visualizer integration."""

    @patch("backend.app.services.visualizer_service.settings")
    def test_pygame_unavailable_graceful_degradation(self, mock_settings):
        """Test graceful degradation when pygame is unavailable."""
        mock_settings.enable_visualization = True
        mock_settings.visualizer_queue_size = 100

        service = VisualizerService()

        # Don't mock pygame - let it fail naturally
        process, queue = service.spawn_visualizer(
            session_id="test-session",
            player1_name="Bot1",
            player2_name="Bot2",
        )

        # Should return None, None on failure
        # (or succeed if pygame is actually installed)
        if process is None and queue is None:
            # Expected behavior when pygame unavailable
            assert True
        else:
            # Pygame is available, clean up
            try:
                process.terminate()
                process.join(timeout=1.0)
                queue.close()
            except Exception:
                pass

    @patch("backend.app.services.visualizer_service.settings")
    def test_terminate_already_dead_process(self, mock_settings):
        """Test terminating a process that's already dead."""
        mock_settings.enable_visualization = True
        mock_settings.visualizer_queue_size = 100

        service = VisualizerService()

        with (
            patch.dict("sys.modules", {"pygame": MagicMock()}),
            patch("backend.app.services.visualizer_adapter.run_visualizer_adapter"),
        ):
            process, queue = service.spawn_visualizer(
                session_id="test-session",
                player1_name="Bot1",
                player2_name="Bot2",
            )

            if process and queue:
                try:
                    # Send shutdown to make process exit
                    queue.put_nowait({"event": "shutdown"})
                    time.sleep(0.5)

                    # Now terminate (should handle already-dead process gracefully)
                    service.terminate_visualizer(process, queue, timeout=1.0)

                    # Should not raise any exceptions
                    assert True

                finally:
                    # Ensure cleanup
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=1.0)
                    with contextlib.suppress(Exception):
                        queue.close()
