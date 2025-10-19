"""Adapter for integrating backend events with pygame visualizer."""

import logging
import multiprocessing
import queue
import sys
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VisualizerAdapter:
    """Adapts backend events to visualizer-compatible format."""

    def __init__(
        self,
        session_id: str,
        event_queue: multiprocessing.Queue,
        player1_name: str,
        player2_name: str,
        player1_sprite: Optional[str] = None,
        player2_sprite: Optional[str] = None,
    ):
        """Initialize the visualizer adapter.

        Args:
            session_id: Session identifier
            event_queue: Queue to receive events from parent process
            player1_name: Name of player 1
            player2_name: Name of player 2
            player1_sprite: Optional sprite path for player 1
            player2_sprite: Optional sprite path for player 2

        """
        self._session_id = session_id
        self._queue = event_queue
        self._player1_name = player1_name
        self._player2_name = player2_name
        self._player1_sprite = player1_sprite
        self._player2_sprite = player2_sprite
        self._visualizer: Optional[Any] = None
        self._states: list[dict[str, Any]] = []
        self._logger = logging.getLogger(__name__)
        self._running = True

    def initialize_visualizer(self) -> None:
        """Initialize pygame and create Visualizer instance immediately.

        Raises:
            ImportError: If pygame is not available
            Exception: If visualizer initialization fails

        """
        try:
            # Import pygame here to avoid importing in parent process
            import pygame  # noqa: F401

            pygame.init()
            self._logger.info(f"Pygame initialized for session {self._session_id}")

            # Import the existing Visualizer class
            from simulator.visualizer import Visualizer

            # Create mock bot objects for the visualizer
            # The visualizer expects BotInterface objects, but we only need name and sprite paths
            class MockBot:
                def __init__(self, name: str, sprite_path: Optional[str], minion_sprite_path: Optional[str]):
                    self.name = name
                    self.sprite_path = sprite_path or "assets/wizards/sample_bot1.png"
                    self.minion_sprite_path = minion_sprite_path or "assets/minions/minion_1.png"

            # Create mock logger for visualizer
            class MockLogger:
                def __init__(self):
                    self.damage_events = []
                    self.spells = []

            mock_logger = MockLogger()
            bot1 = MockBot(
                self._player1_name,
                self._player1_sprite,
                self._player1_sprite.replace("wizards", "minions") if self._player1_sprite else None,
            )
            bot2 = MockBot(
                self._player2_name,
                self._player2_sprite,
                self._player2_sprite.replace("wizards", "minions") if self._player2_sprite else None,
            )

            # Create visualizer instance - this creates the pygame window
            self._visualizer = Visualizer(mock_logger, bot1, bot2)
            self._logger.info(f"Visualizer window created for session {self._session_id}")

        except ImportError as exc:
            self._logger.error(f"Pygame not available for session {self._session_id}: {exc}")
            raise
        except Exception as exc:
            self._logger.error(f"Failed to initialize visualizer for session {self._session_id}: {exc}", exc_info=True)
            raise

    def process_events(self) -> None:
        """Consume events from queue and render game states.

        This method runs in the child process and consumes events from the IPC queue.
        It accumulates game states and renders them in real-time. The window remains
        open after game completion until manually closed by user or admin shutdown.
        """
        self._logger.info(f"Starting event processing for session {self._session_id}")

        try:
            while self._running:
                try:
                    # Non-blocking poll with timeout to allow pygame event handling
                    event_data = self._queue.get(timeout=0.1)

                    event_type = event_data.get("event")
                    self._logger.debug(f"Received event: {event_type}")

                    if event_type == "turn_update":
                        self.handle_turn_event(event_data)
                    elif event_type == "game_over":
                        self.handle_game_over_event(event_data)
                        # Game is over, but keep window open to show final state
                        # Window will close only on user action (closing window) or admin shutdown
                    elif event_type == "shutdown":
                        self._logger.info(f"Received shutdown signal for session {self._session_id}")
                        self._running = False
                    else:
                        self._logger.warning(f"Unknown event type: {event_type}")

                except queue.Empty:
                    # No event available, check for pygame events
                    self._handle_pygame_events()
                    continue

        except Exception as exc:
            self._logger.error(f"Error in event processing loop for session {self._session_id}: {exc}", exc_info=True)
        finally:
            self._logger.info(f"Event processing ended for session {self._session_id}")

    def handle_turn_event(self, event: dict[str, Any]) -> None:
        """Process a turn_update event and render it in real-time.

        Args:
            event: Turn event data containing game state

        """
        try:
            game_state = event.get("game_state")
            turn = event.get("turn", 0)
            if not game_state:
                self._logger.warning("Turn event missing game_state")
                return

            if not self._visualizer:
                self._logger.warning("Visualizer not initialized, cannot render turn")
                return

            # Store previous state for animation
            prev_state = self._states[-1] if self._states else None

            # Accumulate game states
            self._states.append(game_state)

            # Render in real-time
            if prev_state:
                # Animate transition from previous state to current state
                self._visualizer.animate_transition(prev_state, game_state, len(self._states) - 2)
                self._visualizer.wait_for(0.5)  # ANIMATION_DURATION
            else:
                # First state - just render it
                self._visualizer.info_bar_state = game_state
                self._visualizer.render_frame(game_state, turn)
                self._visualizer.wait_for(0.3)

            # Update info bar
            self._visualizer.info_bar_state = game_state
            self._visualizer.draw_wizard_info_bar()

            self._logger.debug(f"Rendered turn {turn} for session {self._session_id}")

        except Exception as exc:
            self._logger.error(f"Error handling turn event: {exc}", exc_info=True)

    def handle_game_over_event(self, event: dict[str, Any]) -> None:
        """Process a game_over event and display end game message.

        Args:
            event: Game over event data containing final state and winner

        """
        try:
            final_state = event.get("final_state")
            winner_name = event.get("winner_name")

            if not self._visualizer:
                self._logger.warning("Visualizer not initialized, cannot show game over")
                return

            # Render final state if provided and not already rendered
            if final_state:
                prev_state = self._states[-1] if self._states else None
                if prev_state and prev_state != final_state:
                    self._visualizer.animate_transition(prev_state, final_state, len(self._states) - 1)
                    self._visualizer.wait_for(0.5)
                    self._states.append(final_state)

            self._logger.info(f"Game over for session {self._session_id}, winner: {winner_name}")

            # Display end game message
            # has_more_matches=False since we're only visualizing one match
            # This method blocks until the user clicks the EXIT button
            self._visualizer.display_end_game_message(winner_name, has_more_matches=False)

            # User clicked EXIT button, signal the visualizer to exit
            self._logger.info(f"User clicked EXIT, closing visualizer for session {self._session_id}")
            self._running = False

        except Exception as exc:
            self._logger.error(f"Error handling game over event: {exc}", exc_info=True)

    def _handle_pygame_events(self) -> None:
        """Handle pygame events (window close, etc.)."""
        try:
            import pygame

            # Only handle events if pygame display is initialized
            # This prevents "video system not initialized" errors
            if pygame.display.get_init():
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._logger.info(f"Pygame QUIT event received for session {self._session_id}")
                        self._running = False

        except ImportError:
            # Pygame not available, skip event handling
            pass
        except Exception as exc:
            self._logger.error(f"Error handling pygame events: {exc}", exc_info=True)

    def shutdown(self) -> None:
        """Clean shutdown of pygame."""
        try:
            import pygame

            pygame.quit()
            self._logger.info(f"Pygame shut down for session {self._session_id}")
        except ImportError:
            # Pygame not available, nothing to shut down
            pass
        except Exception as exc:
            self._logger.error(f"Error shutting down pygame: {exc}", exc_info=True)


def run_visualizer_adapter(
    session_id: str,
    event_queue: multiprocessing.Queue,
    player1_name: str,
    player2_name: str,
    player1_sprite: Optional[str] = None,
    player2_sprite: Optional[str] = None,
) -> None:
    """Entry point for running the visualizer adapter in a child process.

    This function is called by VisualizerService._visualizer_process_main().

    Args:
        session_id: Session identifier
        event_queue: Queue to receive events from parent process
        player1_name: Name of player 1
        player2_name: Name of player 2
        player1_sprite: Optional sprite path for player 1
        player2_sprite: Optional sprite path for player 2

    """
    # Set up logging for child process
    logging.basicConfig(
        level=logging.INFO,
        format=f"[Visualizer-{session_id}] %(levelname)s: %(message)s",
        stream=sys.stdout,
    )
    child_logger = logging.getLogger(__name__)

    try:
        child_logger.info(f"Visualizer adapter starting for session {session_id}")

        # Create adapter instance
        adapter = VisualizerAdapter(
            session_id=session_id,
            event_queue=event_queue,
            player1_name=player1_name,
            player2_name=player2_name,
            player1_sprite=player1_sprite,
            player2_sprite=player2_sprite,
        )

        # Initialize pygame
        adapter.initialize_visualizer()

        # Start event processing loop
        adapter.process_events()

        # Clean shutdown
        adapter.shutdown()

        child_logger.info(f"Visualizer adapter exiting cleanly for session {session_id}")

    except Exception as exc:
        child_logger.error(f"Error in visualizer adapter: {exc}", exc_info=True)
        sys.exit(1)
