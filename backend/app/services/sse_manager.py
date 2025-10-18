"""SSE connection management and event broadcasting."""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..models.events import Event, HeartbeatEvent

logger = logging.getLogger(__name__)


class SSEStream:
    """Represents a single client's event queue."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._closed = False

    async def push(self, event_json: str) -> None:
        if not self._closed:
            await self._queue.put(event_json)

    async def close(self) -> None:
        self._closed = True
        await self._queue.put("__CLOSE__")

    async def stream(self) -> AsyncGenerator[str, None]:
        try:
            while True:
                item = await self._queue.get()
                if item == "__CLOSE__":
                    break
                # Parse the JSON to extract the event type for proper SSE formatting
                try:
                    import json

                    parsed = json.loads(item)
                    event_type = parsed.get("event", "message")
                    yield f"event: {event_type}\ndata: {item}\n\n"
                except (json.JSONDecodeError, KeyError):
                    # Fallback for malformed JSON
                    yield f"event: message\ndata: {item}\n\n"
        finally:
            self._closed = True


class SSEManager:
    """Manages SSE connections per session and broadcasting of events."""

    def __init__(self) -> None:
        self._streams_by_session: Dict[str, List[SSEStream]] = {}
        self._lock = asyncio.Lock()

    async def add_connection(self, session_id: str) -> SSEStream:
        stream = SSEStream()
        async with self._lock:
            self._streams_by_session.setdefault(session_id, []).append(stream)
        return stream

    async def remove_connection(self, session_id: str, stream: SSEStream) -> None:
        async with self._lock:
            streams = self._streams_by_session.get(session_id, [])
            if stream in streams:
                streams.remove(stream)
            if not streams and session_id in self._streams_by_session:
                self._streams_by_session.pop(session_id, None)

    async def broadcast(self, session_id: str, event: Event) -> None:
        """Broadcast an event to all connected clients for a session."""
        try:
            payload = event.model_dump_json()
            async with self._lock:
                streams = list(self._streams_by_session.get(session_id, []))
            for stream in streams:
                await stream.push(payload)
        except Exception as exc:
            logger.error(f"SSE broadcast failed: {exc}")

    async def close_session_streams(self, session_id: str) -> None:
        """Close all SSE streams for a session."""
        async with self._lock:
            streams = self._streams_by_session.get(session_id, [])
            for stream in streams:
                await stream.close()
            # Remove session from tracking
            self._streams_by_session.pop(session_id, None)

    async def heartbeat(self, session_id: str) -> None:
        await self.broadcast(session_id, HeartbeatEvent())

    def get_connection_count(self) -> int:
        """Get total number of active SSE connections across all sessions.

        Returns:
            Total connection count
        """
        total = 0
        for streams in self._streams_by_session.values():
            total += len(streams)
        return total

    async def disconnect_all(self) -> None:
        """Disconnect all SSE connections across all sessions.

        Used during server shutdown to gracefully close all client connections.
        """
        logger.info("Disconnecting all SSE connections...")
        async with self._lock:
            session_ids = list(self._streams_by_session.keys())

        for session_id in session_ids:
            await self.close_session_streams(session_id)

        logger.info(f"Disconnected all SSE connections ({len(session_ids)} sessions)")
