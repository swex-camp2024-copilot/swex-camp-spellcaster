"""Replay endpoint for streaming recorded turn events without delays (Task 8.2)."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..models.events import ReplayTurnEvent
from ..services.runtime import match_logger, session_manager
from ..services.session_manager import SessionNotFoundError as _SessionNotFoundError


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/playground/{session_id}/replay")
async def replay_session_events(session_id: str, request: Request) -> StreamingResponse:
    """Stream recorded turn events in rapid succession (no timing delays)."""
    # Validate session exists or recently finished (we keep state in memory)
    try:
        # If session is gone, we still allow replay if logger has events
        ctx = await session_manager.get_session(session_id)
        _ = ctx  # unused
    except _SessionNotFoundError:
        # Fallback: allow replay only if we have any logged events; else 404
        events = match_logger.get_turn_events(session_id) if match_logger else []
        if not events:
            raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            events = match_logger.get_turn_events(session_id) if match_logger else []
            # Convert TurnEvent -> ReplayTurnEvent and emit quickly
            for ev in events:
                replay = ReplayTurnEvent(
                    turn=ev.turn,
                    game_state=ev.game_state,
                    actions=ev.actions,
                    events=ev.events,
                    log_line=ev.log_line,
                )
                payload = replay.model_dump_json()
                chunk = f"event: replay_turn\ndata: {payload}\n\n"
                # Emit chunk immediately; optional tiny yield to avoid hogging loop
                yield chunk
                await asyncio.sleep(0)
        except Exception as exc:
            logger.error(f"Replay streaming failed: {exc}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

