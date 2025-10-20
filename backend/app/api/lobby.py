"""Lobby API endpoints for PvP matchmaking."""

import logging

from fastapi import APIRouter, HTTPException

from ..models.lobby import LobbyJoinRequest, LobbyMatchResponse
from ..services import runtime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/lobby/join", response_model=LobbyMatchResponse)
async def join_lobby(request: LobbyJoinRequest) -> LobbyMatchResponse:
    """Join lobby queue and wait for match (long-polling).

    This endpoint blocks until a match is found. When 2+ players are in queue,
    they are automatically matched and a game session is created with
    visualization enabled.

    The request will block for up to 5 minutes (300 seconds) waiting for a match.
    If no match is found within that time, the request will timeout.

    Args:
        request: Lobby join request with player_id and bot_config

    Returns:
        LobbyMatchResponse with session_id and opponent details

    Raises:
        PlayerNotFoundError: If player_id doesn't exist in database (404)
        PlayerAlreadyInLobbyError: If player is already in lobby queue (409)
        RuntimeError: If lobby service is not initialized (500)
    """
    # Join queue and wait for match (long-polling)
    # Exceptions are handled by FastAPI's registered exception handlers
    match_response = await runtime.lobby_service.join_queue(request)

    logger.info(
        f"Lobby match created: {match_response.session_id}, "
        f"players: {request.player_id} vs {match_response.opponent_id}"
    )

    return match_response


@router.get("/lobby/status")
async def get_lobby_status() -> dict:
    """Get current lobby queue status.

    Returns:
        Dictionary with queue_size
    """
    try:
        queue_size = await runtime.lobby_service.get_queue_size()
        return {"queue_size": queue_size}

    except Exception as exc:
        logger.error(f"Failed to get lobby status: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get lobby status: {str(exc)}") from exc


@router.delete("/lobby/leave/{player_id}")
async def leave_lobby(player_id: str) -> dict:
    """Remove a player from the lobby queue.

    Args:
        player_id: Player to remove from queue

    Returns:
        Success message

    Raises:
        HTTPException 404: If player is not in queue
    """
    try:
        removed = await runtime.lobby_service.remove_from_queue(player_id)

        if not removed:
            raise HTTPException(status_code=404, detail=f"Player {player_id} is not in lobby queue")

        return {"message": f"Player {player_id} removed from lobby queue"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to remove player from lobby: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove from lobby: {str(exc)}") from exc
