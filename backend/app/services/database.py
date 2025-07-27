"""Database service for centralized database operations in the Spellcasters Playground Backend."""

import logging
from typing import List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel

from ..core.database import async_session_factory
from ..core.exceptions import DatabaseError, PlayerNotFoundError
from ..models.database import GameResultDB, PlayerDB, SessionDB
from ..models.players import Player, PlayerRegistration
from ..models.results import GameResult

logger = logging.getLogger(__name__)


class DatabaseService:
    """Centralized database operations for all models."""

    def __init__(self):
        """Initialize the database service."""
        self._session_factory = async_session_factory

    # Player Operations

    async def create_player(self, registration: PlayerRegistration) -> Player:
        """Create a new player in the database."""
        try:
            async with self._session_factory() as session:
                # Generate unique player ID
                player_id = str(uuid4())

                # Create database record
                player_db = PlayerDB(
                    player_id=player_id,
                    player_name=registration.player_name,
                    submitted_from=registration.submitted_from,
                    sprite_path=registration.sprite_path,
                    minion_sprite_path=registration.minion_sprite_path,
                )

                session.add(player_db)
                await session.commit()
                await session.refresh(player_db)

                # Convert to Player model for return
                player = Player(
                    player_id=player_db.player_id,
                    player_name=player_db.player_name,
                    submitted_from=player_db.submitted_from,
                    sprite_path=player_db.sprite_path,
                    minion_sprite_path=player_db.minion_sprite_path,
                    total_matches=player_db.total_matches,
                    wins=player_db.wins,
                    losses=player_db.losses,
                    draws=player_db.draws,
                    created_at=player_db.created_at,
                    is_builtin=player_db.is_builtin,
                )

                logger.info(f"Created player: {player_id} ({registration.player_name})")
                return player

        except Exception as e:
            logger.error(f"Error creating player: {e}")
            raise DatabaseError(f"Failed to create player: {str(e)}")

    async def get_player(self, player_id: str) -> Optional[Player]:
        """Retrieve player from database by ID."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(select(PlayerDB).where(PlayerDB.player_id == player_id))
                player_db = result.scalar_one_or_none()

                if not player_db:
                    return None

                # Convert to Player model
                return Player(
                    player_id=player_db.player_id,
                    player_name=player_db.player_name,
                    submitted_from=player_db.submitted_from,
                    sprite_path=player_db.sprite_path,
                    minion_sprite_path=player_db.minion_sprite_path,
                    total_matches=player_db.total_matches,
                    wins=player_db.wins,
                    losses=player_db.losses,
                    draws=player_db.draws,
                    created_at=player_db.created_at,
                    is_builtin=player_db.is_builtin,
                )

        except Exception as e:
            logger.error(f"Error retrieving player {player_id}: {e}")
            raise DatabaseError(f"Failed to retrieve player: {str(e)}")

    async def update_player_stats(self, player_id: str, result: GameResult) -> None:
        """Update player statistics in database after a match."""
        try:
            async with self._session_factory() as session:
                result_db = await session.execute(select(PlayerDB).where(PlayerDB.player_id == player_id))
                player_db = result_db.scalar_one_or_none()

                if not player_db:
                    raise PlayerNotFoundError(player_id)

                # Update statistics
                player_db.total_matches += 1
                if result.winner == player_id:
                    player_db.wins += 1
                elif result.result_type.value == "draw":
                    player_db.draws += 1
                else:
                    player_db.losses += 1

                await session.commit()
                logger.info(f"Updated stats for player {player_id}: {result.result_type}")

        except PlayerNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating player stats for {player_id}: {e}")
            raise DatabaseError(f"Failed to update player stats: {str(e)}")

    async def list_all_players(self, include_builtin: bool = True) -> List[Player]:
        """List all players from database."""
        try:
            async with self._session_factory() as session:
                query = select(PlayerDB)
                if not include_builtin:
                    query = query.where(PlayerDB.is_builtin == False)

                result = await session.execute(query)
                players_db = result.scalars().all()

                # Convert to Player models
                players = []
                for player_db in players_db:
                    player = Player(
                        player_id=player_db.player_id,
                        player_name=player_db.player_name,
                        submitted_from=player_db.submitted_from,
                        sprite_path=player_db.sprite_path,
                        minion_sprite_path=player_db.minion_sprite_path,
                        total_matches=player_db.total_matches,
                        wins=player_db.wins,
                        losses=player_db.losses,
                        draws=player_db.draws,
                        created_at=player_db.created_at,
                        is_builtin=player_db.is_builtin,
                    )
                    players.append(player)

                return players

        except Exception as e:
            logger.error(f"Error listing players: {e}")
            raise DatabaseError(f"Failed to list players: {str(e)}")

    async def create_builtin_player(self, player: Player) -> None:
        """Create a built-in player in the database."""
        try:
            async with self._session_factory() as session:
                # Check if player already exists
                result = await session.execute(select(PlayerDB).where(PlayerDB.player_id == player.player_id))
                existing = result.scalar_one_or_none()

                if existing:
                    logger.debug(f"Built-in player {player.player_id} already exists")
                    return

                # Create database record
                player_db = PlayerDB(
                    player_id=player.player_id,
                    player_name=player.player_name,
                    submitted_from=player.submitted_from,
                    sprite_path=player.sprite_path,
                    minion_sprite_path=player.minion_sprite_path,
                    total_matches=player.total_matches,
                    wins=player.wins,
                    losses=player.losses,
                    draws=player.draws,
                    created_at=player.created_at,
                    is_builtin=True,  # Always true for built-in players
                )

                session.add(player_db)
                await session.commit()
                logger.info(f"Created built-in player: {player.player_id} ({player.player_name})")

        except Exception as e:
            logger.error(f"Error creating built-in player {player.player_id}: {e}")
            raise DatabaseError(f"Failed to create built-in player: {str(e)}")

    # Session Operations

    async def create_session_record(self, session_id: str, player_1_id: str, player_2_id: str) -> SessionDB:
        """Create session record in database."""
        try:
            async with self._session_factory() as session:
                session_db = SessionDB(
                    session_id=session_id,
                    player_1_id=player_1_id,
                    player_2_id=player_2_id,
                    status="active",
                )

                session.add(session_db)
                await session.commit()
                await session.refresh(session_db)

                logger.info(f"Created session record: {session_id}")
                return session_db

        except Exception as e:
            logger.error(f"Error creating session record {session_id}: {e}")
            raise DatabaseError(f"Failed to create session record: {str(e)}")

    async def get_active_sessions(self) -> List[SessionDB]:
        """Get all active sessions for admin endpoint."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(SessionDB)
                    .where(SessionDB.status == "active")
                    .options(selectinload(SessionDB.player_1), selectinload(SessionDB.player_2))
                )
                sessions = result.scalars().all()
                return sessions

        except Exception as e:
            logger.error(f"Error retrieving active sessions: {e}")
            raise DatabaseError(f"Failed to retrieve active sessions: {str(e)}")

    async def complete_session(self, session_id: str, result: GameResult) -> None:
        """Mark session as completed and store result."""
        try:
            async with self._session_factory() as session:
                # Update session status
                session_result = await session.execute(select(SessionDB).where(SessionDB.session_id == session_id))
                session_db = session_result.scalar_one_or_none()

                if session_db:
                    session_db.status = "completed"
                    session_db.completed_at = result.created_at
                    session_db.winner_id = result.winner

                # Create game result record
                game_result_db = GameResultDB(
                    session_id=result.session_id,
                    winner_id=result.winner,
                    loser_id=result.loser,
                    result_type=result.result_type.value,
                    total_rounds=result.total_rounds,
                    game_duration=result.game_duration,
                    end_condition=result.end_condition,
                    created_at=result.created_at,
                )

                session.add(game_result_db)
                await session.commit()

                logger.info(f"Completed session {session_id} with result: {result.result_type}")

        except Exception as e:
            logger.error(f"Error completing session {session_id}: {e}")
            raise DatabaseError(f"Failed to complete session: {str(e)}")

    # Migration and Utility Operations

    async def ensure_tables_exist(self) -> None:
        """Ensure all database tables exist (for migration support)."""
        try:
            from ..core.database import create_tables

            await create_tables()
            logger.info("Database tables verified/created successfully")

        except Exception as e:
            logger.error(f"Error ensuring tables exist: {e}")
            raise DatabaseError(f"Failed to create/verify tables: {str(e)}")

    async def health_check(self) -> bool:
        """Perform database health check."""
        try:
            async with self._session_factory() as session:
                # Simple query to test connection
                result = await session.execute(select(1))
                result.scalar_one()
                return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False 