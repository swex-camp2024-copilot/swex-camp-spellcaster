"""Command-line runner for the Spellcasters SSE client.

Example:
  curl -s -X POST http://localhost:8000/playground/start -H 'Content-Type: application/json' -d '{"player_1_config":{"player_id":"builtin_sample_1","bot_type":"builtin","bot_id":"sample_bot_1"},"player_2_config":{"player_id":"builtin_sample_2","bot_type":"builtin","bot_id":"sample_bot_2"}}' | jq -r .session_id
  uv run python -m backend.client.sse_client_main \
    --base-url http://localhost:8000 \
    --session-id <SESSION_ID> \
    --max-events 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from typing import Any, Dict

# Support running as a script (no package parent)
try:
    # When executed as a module within the package
    from .sse_client import SSEClient, SSEClientConfig  # type: ignore
except Exception:  # pragma: no cover
    # When executed directly: python backend/client/sse_client_main.py
    from backend.client.sse_client import SSEClient, SSEClientConfig  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spellcasters SSE client")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SPELLCASTERS_BASE_URL", "http://localhost:8000"),
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--session-id",
        default=os.environ.get("SPELLCASTERS_SESSION_ID"),
        required=False,
        help="Session ID to connect to (or set SPELLCASTERS_SESSION_ID)",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=20,
        help="Stop after receiving this many events (default: 20)",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    return parser.parse_args()


async def run_client(base_url: str, session_id: str, max_events: int) -> None:
    config = SSEClientConfig()
    async with SSEClient(base_url, session_id, config=config).connect() as client:
        count = 0
        async for event in client.events():
            _print_event(event)
            count += 1
            if count >= max_events:
                break


def _print_event(event: Dict[str, Any]) -> None:
    try:
        print(json.dumps(event, ensure_ascii=False))
    except Exception:
        # Fallback to raw printing
        print(event)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))

    if not args.session_id:
        raise SystemExit("--session-id is required (or set SPELLCASTERS_SESSION_ID)")

    try:
        asyncio.run(run_client(args.base_url, args.session_id, args.max_events))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
