"""SSE streaming endpoints."""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..services.runtime import sse_manager, session_manager
from ..services.session_manager import SessionNotFoundError as _SessionNotFoundError
from ..models.events import HeartbeatEvent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/playground/{session_id}/events")
async def stream_session_events(session_id: str, request: Request) -> StreamingResponse:
    """Stream real-time session events over Server-Sent Events (SSE)."""
    # Validate session exists
    try:
        await session_manager.get_session(session_id)
    except _SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    stream = await sse_manager.add_connection(session_id)

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
            await sse_manager.remove_connection(session_id, stream)
            await stream.close()

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

