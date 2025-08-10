"""Admin API endpoints (Task 9.2). No auth for hackathon scope."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from ..services.runtime import admin_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/admin/players")
async def list_admin_players() -> List[dict]:
    """List all registered players with stats (built-in included)."""
    infos = await admin_service.list_all_players()
    # Return as dicts for JSON response
    return [info.__dict__ for info in infos]


@router.get("/playground/active")
async def list_active_sessions() -> List[dict]:
    """List currently active playground sessions."""
    infos = await admin_service.get_active_sessions()
    return [info.__dict__ for info in infos]


@router.delete("/playground/{session_id}")
async def admin_cleanup_session(session_id: str) -> dict:
    """Terminate a session and close SSE streams (best-effort)."""
    ok = await admin_service.cleanup_session(session_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to cleanup session")
    return {"status": "terminated", "session_id": session_id}

