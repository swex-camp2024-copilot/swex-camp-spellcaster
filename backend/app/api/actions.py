"""Action submission API for the Playground backend (Task 7.1)."""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..models.actions import PlayerAction, ActionData
from ..services import runtime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/playground/{session_id}/action")
async def submit_action(session_id: str, payload: PlayerAction) -> Dict[str, str]:
    """Submit an action for a given session/turn."""
    try:
        # Validate session and turn
        ctx = await runtime.session_manager.get_session(session_id)
        expected_turn = ctx.game_state.turn_index + 1
        if payload.turn != expected_turn:
            raise HTTPException(status_code=400, detail=f"Invalid turn: expected {expected_turn}, got {payload.turn}")

        # Validate player belongs to session
        if payload.player_id not in (ctx.game_state.player_1.player_id, ctx.game_state.player_2.player_id):
            raise HTTPException(status_code=400, detail="player_id is not part of this session")

        # Basic turn validation will be handled in SessionManager collection
        await runtime.session_manager.submit_action(
            session_id=session_id,
            player_id=payload.player_id,
            turn=payload.turn,
            action=ActionData(**payload.action_data),
        )
        return {"status": "accepted"}
    except Exception as exc:
        logger.error(f"Failed to submit action: {exc}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid action submission")

