"""Command-line runner for the Spellcasters Bot Client simulator (moved)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from typing import Any

from .bot_client import BotClient, PlayerRegistrationRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spellcasters Bot Client Simulator")
    parser.add_argument("--base-url", default=os.environ.get("SPELLCASTERS_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--player-name", default=os.environ.get("SPELLCASTERS_PLAYER_NAME", "CLI Bot"))
    parser.add_argument("--builtin-bot-id", default=os.environ.get("SPELLCASTERS_BUILTIN_BOT_ID", "sample_bot_1"))
    parser.add_argument("--max-events", type=int, default=int(os.environ.get("SPELLCASTERS_MAX_EVENTS", "10")))
    parser.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO"), choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


async def run_bot(base_url: str, player_name: str, builtin_bot_id: str, max_events: int) -> None:
    client = BotClient(base_url)
    try:
        player = await client.register_player(PlayerRegistrationRequest(player_name=player_name))
        print(json.dumps({"registered_player": player.__dict__}))
        session_id = await client.start_match_vs_builtin(player.player_id, builtin_bot_id)
        print(json.dumps({"session_id": session_id}))
        async for event in client.stream_session_events(session_id, max_events=max_events):
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
        asyncio.run(run_bot(args.base_url, args.player_name, args.builtin_bot_id, args.max_events))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()


