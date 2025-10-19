"""SSE streaming endpoints."""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..core.exceptions import SessionNotFoundError
from ..services import runtime
from ..models.events import HeartbeatEvent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/playground/{session_id}/events")
async def stream_session_events(session_id: str, request: Request) -> StreamingResponse:
    """Stream real-time session events over Server-Sent Events (SSE)."""
    # Validate session exists
    try:
        await runtime.session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise  # Re-raise to be handled by custom error handler

    stream = await runtime.sse_manager.add_connection(session_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Immediately yield a first heartbeat so clients see data promptly
            heartbeat_json = HeartbeatEvent().model_dump_json()
            heartbeat_data = f"event: heartbeat\ndata: {heartbeat_json}\n\n"
            yield heartbeat_data

            # Then yield from the stream while connection is open
            async for chunk in stream.stream():
                if await request.is_disconnected():
                    break
                yield chunk
        finally:
            await runtime.sse_manager.remove_connection(session_id, stream)
            await stream.close()

            # Check if this was the last connection for a completed session
            # If so, clean up the session resources (including visualizer)
            try:
                ctx = await runtime.session_manager.get_session(session_id)
                # Only cleanup if game is over and no more SSE connections
                if ctx.game_state.status != "active":
                    connection_count = len(runtime.sse_manager._streams_by_session.get(session_id, []))
                    if connection_count == 0:
                        logger.info(f"Last client disconnected from completed session {session_id}, triggering cleanup")
                        await runtime.session_manager.cleanup_session(session_id)
            except Exception as exc:
                logger.debug(f"Session {session_id} already cleaned up or not found: {exc}")

    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    # Explicitly set background to close stream on client disconnect
    return response
