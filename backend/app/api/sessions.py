"""Session API endpoints for the Playground backend."""

import logging
from typing import Dict

from fastapi import APIRouter

from ..services.session_manager import SessionManager
from ..models.players import PlayerConfig

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/playground/start")
async def start_playground_match(payload: Dict) -> Dict[str, str]:
    """Start a new playground session and return its session_id."""
    # Extract player configurations
    p1_cfg = PlayerConfig(**payload["player_1_config"])  # type: ignore[index]
    p2_cfg = PlayerConfig(**payload["player_2_config"])  # type: ignore[index]

    manager = SessionManager()
    session_id = await manager.create_session(p1_cfg, p2_cfg)
    return {"session_id": session_id}

