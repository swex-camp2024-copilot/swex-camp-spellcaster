"""Player API endpoints for the Spellcasters Playground Backend."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..core.exceptions import DatabaseError, PlayerNotFoundError, PlayerRegistrationError
from ..models.errors import ErrorResponse
from ..models.players import Player, PlayerRegistration
from ..services.database import DatabaseService
from ..services.player_registry import PlayerRegistry

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/players", tags=["players"])

# Dependency to get database service
async def get_database_service() -> DatabaseService:
    """Get database service instance."""
    return DatabaseService()

# Dependency to get player registry
async def get_player_registry(db_service: DatabaseService = Depends(get_database_service)) -> PlayerRegistry:
    """Get player registry instance."""
    registry = PlayerRegistry(db_service)
    await registry.initialize()
    return registry


@router.post("/register", response_model=Player, status_code=status.HTTP_201_CREATED)
async def register_player(
    registration: PlayerRegistration,
    player_registry: PlayerRegistry = Depends(get_player_registry)
) -> Player:
    """
    Register a new player in the system.
    
    Creates a new player with the provided registration data and returns
    the complete player information including generated UUID.
    
    Args:
        registration: Player registration data including name and submission method
        player_registry: Player registry service (injected)
    
    Returns:
        Player: Complete player information with generated player_id
        
    Raises:
        HTTPException: 400 for validation errors or registration failures
        HTTPException: 500 for internal server errors
    """
    try:
        logger.info(f"Registering new player: {registration.player_name}")
        
        # Register player through registry service
        player = await player_registry.register_player(registration)
        
        logger.info(f"Successfully registered player: {player.player_id} ({player.player_name})")
        return player
        
    except PlayerRegistrationError as e:
        logger.warning(f"Player registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "PLAYER_REGISTRATION_ERROR",
                "message": str(e),
                "player_name": registration.player_name
            }
        )
    except DatabaseError as e:
        logger.error(f"Database error during player registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR", 
                "message": "Failed to register player due to database error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during player registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during registration"
            }
        )


@router.get("/{player_id}", response_model=Player)
async def get_player(
    player_id: str,
    player_registry: PlayerRegistry = Depends(get_player_registry)
) -> Player:
    """
    Get player information by player ID.
    
    Args:
        player_id: Unique player identifier
        player_registry: Player registry service (injected)
    
    Returns:
        Player: Complete player information
        
    Raises:
        HTTPException: 404 if player not found
        HTTPException: 500 for internal server errors
    """
    try:
        logger.debug(f"Retrieving player: {player_id}")
        
        player = await player_registry.get_player(player_id)
        if not player:
            logger.warning(f"Player not found: {player_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "PLAYER_NOT_FOUND",
                    "message": f"Player with ID {player_id} not found",
                    "player_id": player_id
                }
            )
        
        return player
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving player {player_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to retrieve player information"
            }
        )


@router.get("", response_model=List[Player])
async def list_players(
    include_builtin: bool = True,
    player_registry: PlayerRegistry = Depends(get_player_registry)
) -> List[Player]:
    """
    List all players in the system.
    
    Args:
        include_builtin: Whether to include built-in players in results (default: True)
        player_registry: Player registry service (injected)
    
    Returns:
        List[Player]: List of all players
        
    Raises:
        HTTPException: 500 for internal server errors
    """
    try:
        logger.debug(f"Listing players (include_builtin={include_builtin})")
        
        players = await player_registry.list_players(include_builtin=include_builtin)
        
        logger.debug(f"Retrieved {len(players)} players")
        return players
        
    except Exception as e:
        logger.error(f"Error listing players: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to retrieve player list"
            }
        )


@router.get("/builtin/list", response_model=List[Player])
async def list_builtin_players(
    player_registry: PlayerRegistry = Depends(get_player_registry)
) -> List[Player]:
    """
    List all built-in players.
    
    Args:
        player_registry: Player registry service (injected)
    
    Returns:
        List[Player]: List of built-in players
        
    Raises:
        HTTPException: 500 for internal server errors
    """
    try:
        logger.debug("Listing built-in players")
        
        players = await player_registry.list_builtin_players()
        
        logger.debug(f"Retrieved {len(players)} built-in players")
        return players
        
    except Exception as e:
        logger.error(f"Error listing built-in players: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to retrieve built-in player list"
            }
        )


@router.get("/stats/summary")
async def get_player_statistics(
    player_registry: PlayerRegistry = Depends(get_player_registry)
) -> dict:
    """
    Get summary statistics about players in the system.
    
    Args:
        player_registry: Player registry service (injected)
    
    Returns:
        dict: Player statistics summary
        
    Raises:
        HTTPException: 500 for internal server errors
    """
    try:
        logger.debug("Getting player statistics summary")
        
        stats = await player_registry.get_player_statistics_summary()
        
        logger.debug(f"Player statistics: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting player statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to retrieve player statistics"
            }
        )


# Note: Exception handlers are defined in main.py on the FastAPI app instance
# APIRouter does not support exception handlers directly 