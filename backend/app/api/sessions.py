"""Session API endpoints for the Playground backend."""

import logging

from fastapi import APIRouter, HTTPException

from ..models.players import PlayerConfig
from ..models.sessions import SessionCreationRequest
from ..services import runtime

router = APIRouter()
logger = logging.getLogger(__name__)

# Using shared runtime session manager to maintain in-memory sessions across requests


@router.post("/playground/start")
async def start_playground_match(payload: SessionCreationRequest) -> dict[str, str]:
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

        session_id = await runtime.session_manager.create_session(p1_cfg, p2_cfg, visualize=payload.visualize)
        return {"session_id": session_id}

    except HTTPException:
        raise
    except ValueError as exc:
        # Handle player not found and invalid bot configuration errors
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg) from exc
        else:
            raise HTTPException(status_code=400, detail=error_msg) from exc
    except Exception as exc:
        logger.error(f"Failed to start session: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start session") from exc
