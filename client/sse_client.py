"""Async SSE client for the Spellcasters Playground backend (moved from backend/client)."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, AsyncIterator, Dict, Optional

import httpx

try:
    from backend.app.models.events import (
        TurnEvent,
        GameOverEvent,
        HeartbeatEvent,
        ErrorEvent,
        SessionStartEvent,
    )

    _HAVE_BACKEND_MODELS = True
except Exception:
    _HAVE_BACKEND_MODELS = False
    TurnEvent = GameOverEvent = HeartbeatEvent = ErrorEvent = SessionStartEvent = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class SSEClientConfig:
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 30.0
    reconnect_initial_backoff: float = 0.5
    reconnect_max_backoff: float = 8.0
    max_retries: int = 5


class SSEClient:
    def __init__(
        self,
        base_url: str,
        session_id: str,
        *,
        config: Optional[SSEClientConfig] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id
        self.config = config or SSEClientConfig()
        self._external_client = client is not None
        self._client = client
        self._stop = asyncio.Event()

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/playground/{self.session_id}/events"

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator["SSEClient", None]:
        if self._client is None:
            timeout = httpx.Timeout(
                connect=self.config.connect_timeout_seconds,
                read=self.config.read_timeout_seconds,
                write=self.config.read_timeout_seconds,
                pool=self.config.connect_timeout_seconds,
            )
            self._client = httpx.AsyncClient(timeout=timeout)
        try:
            yield self
        finally:
            await self.close()

    async def close(self) -> None:
        self._stop.set()
        if self._client and not self._external_client:
            try:
                await self._client.aclose()
            finally:
                self._client = None

    async def stop(self) -> None:
        self._stop.set()

    async def events(self) -> AsyncIterator[Dict[str, Any]]:
        assert self._client is not None, "Call connect() context manager first"
        backoff = self.config.reconnect_initial_backoff
        retries = 0
        while not self._stop.is_set():
            try:
                async with self._client.stream("GET", self.endpoint, headers={"Accept": "text/event-stream"}) as resp:
                    if resp.status_code != 200:
                        raise httpx.HTTPStatusError("SSE connect failed", request=resp.request, response=resp)
                    backoff = self.config.reconnect_initial_backoff
                    retries = 0
                    async for event in self._iter_sse(resp):
                        yield self._decode_event(event)
                if self._stop.is_set():
                    break
            except (httpx.TransportError, httpx.HTTPError) as exc:
                retries += 1
                if retries > self.config.max_retries:
                    logger.error(f"SSE reconnect max retries exceeded ({retries}/{self.config.max_retries}): {exc}")
                    break
                logger.warning(
                    f"SSE connection error (retry {retries}/{self.config.max_retries}, backoff {backoff:.2f}s): {exc}"
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, self.config.reconnect_max_backoff)

    async def _iter_sse(self, resp: httpx.Response) -> AsyncIterator[Dict[str, str]]:
        assert resp.is_stream_consumed is False
        event_name: Optional[str] = None
        data_lines: list[str] = []
        async for raw_line in resp.aiter_lines():
            if self._stop.is_set():
                break
            line = raw_line.strip()
            if not line:
                if data_lines:
                    payload = "\n".join(data_lines)
                    yield {"event": event_name or "message", "data": payload}
                    data_lines.clear()
                    event_name = None
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
                continue
            if line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
                continue
        if data_lines:
            payload = "\n".join(data_lines)
            yield {"event": event_name or "message", "data": payload}

    def _decode_event(self, sse: Dict[str, str]) -> Dict[str, Any]:
        try:
            data = json.loads(sse.get("data", "{}"))
        except json.JSONDecodeError:
            return {"event": sse.get("event", "message"), "data": sse.get("data")}
        if _HAVE_BACKEND_MODELS and isinstance(data, dict):
            event_type = data.get("event")
            model = None
            if event_type == "turn_update" and TurnEvent is not None:
                model = TurnEvent
            elif event_type == "game_over" and GameOverEvent is not None:
                model = GameOverEvent
            elif event_type == "heartbeat" and HeartbeatEvent is not None:
                model = HeartbeatEvent
            elif event_type == "error" and ErrorEvent is not None:
                model = ErrorEvent
            elif event_type == "session_start" and SessionStartEvent is not None:
                model = SessionStartEvent
            if model is not None:
                try:
                    return model(**data).model_dump()
                except Exception:
                    logger.debug("Failed to decode event with model; returning raw dict")
                    return data
        return data


__all__ = ["SSEClient", "SSEClientConfig"]
