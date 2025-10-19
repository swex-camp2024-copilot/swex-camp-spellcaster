"""Command-line runner for the Spellcasters Bot Client simulator (moved)."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

from .bot_client import BotClient, BotInterfaceAdapter, PlayerRegistrationRequest, RandomWalkStrategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spellcasters Bot Client Simulator")
    parser.add_argument("--base-url", default=os.environ.get("SPELLCASTERS_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--player-name", default=os.environ.get("SPELLCASTERS_PLAYER_NAME", "CLI Bot"))
    parser.add_argument("--builtin-bot-id", default=os.environ.get("SPELLCASTERS_BUILTIN_BOT_ID", "sample_bot_1"))
    parser.add_argument("--max-events", type=int, default=int(os.environ.get("SPELLCASTERS_MAX_EVENTS", "100")))
    parser.add_argument(
        "--log-level", default=os.environ.get("LOG_LEVEL", "INFO"), choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    parser.add_argument(
        "--bot-type",
        default="random",
        choices=["random", "custom"],
        help="Type of bot to use: 'random' for RandomWalkStrategy, 'custom' to load from --bot-path",
    )
    parser.add_argument(
        "--bot-path",
        default=None,
        help="Path to bot module (e.g., 'bots.sample_bot1.sample_bot_1.SampleBot1'). Format: module.path.ClassName",
    )
    return parser.parse_args()


def load_bot_class(bot_path: str) -> Any:
    """Load a bot class from a module path.

    Args:
        bot_path: Module path in format 'module.path.ClassName'

    Returns:
        The bot class

    Raises:
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

    module = importlib.import_module(module_path)
    bot_class = getattr(module, class_name)
    return bot_class


async def run_bot(
    base_url: str,
    player_name: str,
    builtin_bot_id: str,
    max_events: int,
    bot_type: str = "random",
    bot_path: Optional[str] = None,
) -> None:
    # Create bot strategy based on bot_type
    strategy = None
    if bot_type == "custom":
        if not bot_path:
            raise ValueError("--bot-path is required when --bot-type=custom")
        bot_class = load_bot_class(bot_path)
        bot_instance = bot_class()
        strategy = BotInterfaceAdapter(bot_instance)
        print(json.dumps({"bot_loaded": bot_path, "bot_name": getattr(bot_instance, "name", "Unknown")}))
    else:
        strategy = RandomWalkStrategy()
        print(json.dumps({"bot_loaded": "RandomWalkStrategy"}))

    client = BotClient(base_url, strategy=strategy)
    try:
        player = await client.register_player(PlayerRegistrationRequest(player_name=player_name))
        print(json.dumps({"registered_player": player.__dict__}))
        session_id = await client.start_match_vs_builtin(player.player_id, builtin_bot_id, max_events=max_events)
        print(json.dumps({"session_id": session_id}))

        # Play match and automatically submit actions
        async for event in client.play_match(session_id, player.player_id, max_events=max_events):
            try:
                print(json.dumps(event, ensure_ascii=False))
            except Exception:
                print(event)
    finally:
        await client.aclose()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    try:
        asyncio.run(
            run_bot(
                args.base_url,
                args.player_name,
                args.builtin_bot_id,
                args.max_events,
                args.bot_type,
                args.bot_path,
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
