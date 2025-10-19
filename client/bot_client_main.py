"""Command-line runner for the Spellcasters Bot Client simulator (moved)."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import httpx

from .bot_client import BotClient, RandomWalkStrategy


logger = logging.getLogger(__name__)


def get_os_username() -> str:
    """Get the current OS username via whoami command.

    Returns:
        The OS username as a string

    Raises:
        RuntimeError: If username cannot be determined
    """
    try:
        result = subprocess.run(["whoami"], capture_output=True, text=True, check=True, timeout=5)
        username = result.stdout.strip()
        if not username:
            raise RuntimeError("whoami returned empty username")
        return username
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get OS username: {e.stderr}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("whoami command timed out") from e
    except FileNotFoundError as e:
        raise RuntimeError("whoami command not found") from e


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spellcasters Bot Client Simulator")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", "http://localhost:8000"),
        help="Backend server URL (env: BASE_URL)",
    )
    parser.add_argument(
        "--player-id",
        default=os.environ.get("PLAYER_ID"),
        help="Existing registered player ID (default: OS username via whoami, env: PLAYER_ID)",
    )
    parser.add_argument(
        "--opponent-id",
        default=os.environ.get("OPPONENT_ID", "builtin_sample_1"),
        help="Opponent ID: builtin bot or remote player (default: builtin_sample_1, env: OPPONENT_ID)",
    )
    parser.add_argument(
        "--bot-type",
        default=os.environ.get("BOT_TYPE", "random"),
        choices=["random", "custom"],
        help="Bot strategy: random or custom (default: random, env: BOT_TYPE)",
    )
    parser.add_argument(
        "--bot-path",
        default=os.environ.get("BOT_PATH"),
        help="Module path for custom bot (required if --bot-type=custom, env: BOT_PATH). Format: module.path.ClassName",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=int(os.environ.get("MAX_EVENTS", "100")),
        help="Maximum events to process (default: 100, env: MAX_EVENTS)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO, env: LOG_LEVEL)",
    )
    return parser.parse_args()


def load_bot_class(bot_path: str) -> Any:
    """Load a bot class from a module path.

    Args:
        bot_path: Module path in format 'module.path.ClassName'

    Returns:
        The bot class

    Raises:
        ValueError: If bot path format is invalid
        ImportError: If module cannot be loaded
        AttributeError: If class cannot be found
    """
    parts = bot_path.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid bot path: {bot_path}. Expected format: module.path.ClassName")

    class_name = parts[-1]
    module_path = ".".join(parts[:-1])

    # Add current directory to Python path if not already there
    current_dir = str(Path.cwd())
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        module = importlib.import_module(module_path)
        bot_class = getattr(module, class_name)
        return bot_class
    except ImportError as e:
        logger.error(f"Failed to import module '{module_path}': {e}")
        raise
    except AttributeError as e:
        logger.error(f"Failed to find class '{class_name}' in module '{module_path}': {e}")
        raise


async def run_bot(
    base_url: str,
    player_id: str,
    opponent_id: str,
    max_events: int,
    bot_type: str = "random",
    bot_path: Optional[str] = None,
) -> None:
    """Run a bot client match.

    Args:
        base_url: Backend server URL
        player_id: Existing registered player ID
        opponent_id: Opponent ID (builtin bot or remote player)
        max_events: Maximum events to process
        bot_type: Bot strategy type ('random' or 'custom')
        bot_path: Module path for custom bot (required if bot_type='custom')

    Raises:
        ValueError: If bot_path is missing when bot_type='custom'
        RuntimeError: If connection to backend fails
    """
    # Validate bot_path for custom bots
    if bot_type == "custom" and not bot_path:
        raise ValueError("--bot-path is required when --bot-type=custom")

    # Instantiate bot based on bot_type
    bot_instance = None
    if bot_type == "custom":
        try:
            bot_class = load_bot_class(bot_path)
            bot_instance = bot_class()
            logger.info(f"Loaded custom bot: {bot_path} (name: {bot_instance.name})")
            print(json.dumps({"bot_loaded": bot_path, "bot_name": bot_instance.name}))
        except Exception as e:
            logger.error(f"Failed to load custom bot from {bot_path}: {e}")
            raise
    else:
        bot_instance = RandomWalkStrategy()
        logger.info("Using RandomWalkStrategy bot")
        print(json.dumps({"bot_loaded": "RandomWalkStrategy"}))

    # Create client with bot instance
    client = BotClient(base_url, bot_instance=bot_instance)
    try:
        # Start match
        try:
            session_id = await client.start_match(player_id, opponent_id, visualize=True)
            logger.info(f"Started match: session_id={session_id}")
            print(json.dumps({"session_id": session_id, "player_id": player_id, "opponent_id": opponent_id}))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Player '{player_id}' not found. Please register first via POST /players/register")
            else:
                logger.error(f"Failed to start match: HTTP {e.response.status_code} - {e.response.text}")
            raise
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to backend at {base_url}: {e}")
            raise RuntimeError(f"Backend connection failed: {e}") from e

        # Play match and automatically submit actions
        async for event in client.play_match(session_id, player_id, max_events=max_events):
            try:
                print(json.dumps(event, ensure_ascii=False))
            except Exception:
                print(event)

        # Display completion message
        print("Match complete. Press Ctrl+C to exit.")
        # Keep connection alive until user terminates
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass

    finally:
        await client.aclose()


def main() -> None:
    args = parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get player_id (default to OS username if not provided)
    player_id = args.player_id
    if not player_id:
        try:
            player_id = get_os_username()
            logger.info(f"Using OS username as player_id: {player_id}")
        except RuntimeError as e:
            logger.error(f"Failed to get OS username: {e}")
            sys.exit(1)

    try:
        asyncio.run(
            run_bot(
                args.base_url,
                player_id,
                args.opponent_id,
                args.max_events,
                args.bot_type,
                args.bot_path,
            )
        )
    except KeyboardInterrupt:
        logger.info("Client terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
