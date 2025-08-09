"""Session API endpoints for the Playground backend."""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..models.players import PlayerConfig
from ..models.sessions import SessionCreationRequest
from ..services.session_manager import SessionManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Module-level session manager to maintain in-memory sessions across requests
session_manager = SessionManager()


@router.post("/playground/start")
async def start_playground_match(payload: SessionCreationRequest) -> Dict[str, str]:
    """Start a new playground session and return its session_id."""
    try:
        # Validate builtin bot requirements
        def validate_cfg(cfg: PlayerConfig) -> None:
            if cfg.bot_type == "builtin" and not cfg.bot_id:
                raise HTTPException(status_code=400, detail="bot_id is required for builtin bots")

        p1_cfg = PlayerConfig(**payload.player_1_config)
        p2_cfg = PlayerConfig(**payload.player_2_config)
        validate_cfg(p1_cfg)
        validate_cfg(p2_cfg)

        session_id = await session_manager.create_session(p1_cfg, p2_cfg)
        return {"session_id": session_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to start session: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start session")

