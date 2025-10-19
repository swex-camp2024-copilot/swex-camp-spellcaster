"""Visualizer process lifecycle management for the Spellcasters Playground Backend."""

import logging
import multiprocessing
from typing import Optional, Union

from ..core.config import settings
from ..models.events import GameOverEvent, TurnEvent

logger = logging.getLogger(__name__)


class VisualizerService:
    """Manages visualizer process lifecycle and event communication."""

    def __init__(self):
        """Initialize the visualizer service."""
        pass

    def is_visualization_available(self) -> bool:
        """Check if visualization is available.

        Returns:
            True if pygame can be imported and visualization is enabled in config

        """
        if not settings.enable_visualization:
            return False

        try:
            import pygame  # noqa: F401

            return True
        except ImportError:
            return False

    def spawn_visualizer(
        self,
        session_id: str,
        player1_name: str,
        player2_name: str,
        player1_sprite: Optional[str] = None,
        player2_sprite: Optional[str] = None,
    ) -> tuple[Optional[multiprocessing.Process], Optional[multiprocessing.Queue]]:
        """Spawn a visualizer process for a session.

        Args:
            session_id: Unique session identifier
            player1_name: Name of player 1
            player2_name: Name of player 2
            player1_sprite: Optional sprite path for player 1
            player2_sprite: Optional sprite path for player 2

        Returns:
            Tuple of (process, queue) or (None, None) on failure

        """
        try:
            # Check if visualization is available
            if not self.is_visualization_available():
                logger.warning(
                    f"Visualization requested for session {session_id} but not available "
                    "(pygame not installed or visualization disabled in config)"
                )
                return (None, None)

            # Create IPC queue for event communication
            queue = multiprocessing.Queue(maxsize=settings.visualizer_queue_size)

            # Spawn visualizer process
            process = multiprocessing.Process(
                target=self._visualizer_process_main,
                args=(session_id, queue, player1_name, player2_name, player1_sprite, player2_sprite),
                daemon=True,
            )
            process.start()

            logger.info(f"Visualizer spawned for session {session_id} (PID: {process.pid})")
            return (process, queue)

        except Exception as exc:
            logger.error(f"Failed to spawn visualizer for session {session_id}: {exc}", exc_info=True)
            return (None, None)

    def send_event(self, queue: multiprocessing.Queue, event: Union[TurnEvent, GameOverEvent]) -> bool:
        """Send an event to the visualizer process.

        Args:
            queue: IPC queue to send event through
            event: Event to send (TurnEvent or GameOverEvent)

        Returns:
            True if sent successfully, False otherwise

        """
        try:
            # Serialize event to dictionary for IPC
            event_data = event.model_dump()
            queue.put_nowait(event_data)
            return True
        except Exception as exc:
            # Queue full or other error - log and continue
            logger.warning(f"Failed to send event to visualizer: {exc}")
            return False

    def terminate_visualizer(
        self,
        process: multiprocessing.Process,
        queue: Optional[multiprocessing.Queue],
        timeout: float = 5.0,
    ) -> None:
        """Gracefully terminate a visualizer process.

        Args:
            process: Process to terminate
            queue: IPC queue to close (optional)
            timeout: Timeout in seconds for graceful shutdown

        """
        try:
            if process is None:
                return

            # Send shutdown signal via queue if available
            if queue is not None:
                try:
                    shutdown_event = {"event": "shutdown", "reason": "session_ended"}
                    queue.put_nowait(shutdown_event)
                except Exception:
                    pass  # Queue might be full or closed

            # Wait for graceful termination
            process.join(timeout=timeout)

            # Force kill if still alive
            if process.is_alive():
                logger.warning(f"Visualizer process {process.pid} did not terminate gracefully, force killing")
                process.terminate()
                process.join(timeout=1.0)

                # Last resort: kill
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1.0)

            # Close queue
            if queue is not None:
                try:
                    queue.close()
                    queue.join_thread()
                except Exception:
                    pass  # Queue might already be closed

            logger.info(f"Visualizer process {process.pid} terminated")

        except Exception as exc:
            logger.error(f"Error terminating visualizer process: {exc}", exc_info=True)

    @staticmethod
    def _visualizer_process_main(
        session_id: str,
        event_queue: multiprocessing.Queue,
        player1_name: str,
        player2_name: str,
        player1_sprite: Optional[str],
        player2_sprite: Optional[str],
    ) -> None:
        """Entry point for visualizer child process.

        This method runs in a separate process and handles all pygame visualization.

        Args:
            session_id: Session identifier
            event_queue: Queue to receive events from parent process
            player1_name: Name of player 1
            player2_name: Name of player 2
            player1_sprite: Optional sprite path for player 1
            player2_sprite: Optional sprite path for player 2

        """
        # Import visualizer adapter here to avoid importing in parent process
        from .visualizer_adapter import run_visualizer_adapter

        # Run the visualizer adapter (handles logging setup internally)
        run_visualizer_adapter(
            session_id=session_id,
            event_queue=event_queue,
            player1_name=player1_name,
            player2_name=player2_name,
            player1_sprite=player1_sprite,
            player2_sprite=player2_sprite,
        )
