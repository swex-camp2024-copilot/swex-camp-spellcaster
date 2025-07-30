"""Comprehensive tests for the Player Management System."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.app.core.exceptions import DatabaseError, PlayerNotFoundError, PlayerRegistrationError
from backend.app.models.players import Player, PlayerRegistration
from backend.app.models.results import GameResult, GameResultType
from backend.app.services.database import DatabaseService
from backend.app.services.player_registry import PlayerRegistry


class TestDatabaseService:
    """Test database service functionality."""

    @pytest.fixture
    async def db_service(self):
        """Create database service for testing."""
        return DatabaseService()

    @pytest.fixture
    def sample_registration(self):
        """Sample player registration data."""
        return PlayerRegistration(
            player_name="TestPlayer",
            submitted_from="online",
            sprite_path="assets/wizards/test.png"
        )

    @pytest.fixture
    def sample_player(self):
        """Sample player data."""
        return Player(
            player_id=str(uuid4()),
            player_name="TestPlayer",
            submitted_from="online",
            sprite_path="assets/wizards/test.png",
            total_matches=0,
            wins=0,
            losses=0,
            draws=0,
            created_at=datetime.now(),
            is_builtin=False
        )

    @pytest.mark.asyncio
    async def test_create_player_success(self, db_service, sample_registration):
        """Test successful player creation."""
        with patch.object(db_service, '_session_factory') as mock_session_factory:
            # Mock database session and operations
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            
            # Mock player DB object
            mock_player_db = AsyncMock()
            mock_player_db.player_id = "test-uuid"
            mock_player_db.player_name = sample_registration.player_name
            mock_player_db.submitted_from = sample_registration.submitted_from
            mock_player_db.sprite_path = sample_registration.sprite_path
            mock_player_db.minion_sprite_path = sample_registration.minion_sprite_path
            mock_player_db.total_matches = 0
            mock_player_db.wins = 0
            mock_player_db.losses = 0
            mock_player_db.draws = 0
            mock_player_db.created_at = datetime.now()
            mock_player_db.is_builtin = False
            
            mock_session.refresh.side_effect = lambda x: setattr(x, 'player_id', 'test-uuid')

            with patch('uuid.uuid4', return_value='test-uuid'):
                player = await db_service.create_player(sample_registration)

            assert player.player_id == "test-uuid"
            assert player.player_name == sample_registration.player_name
            assert player.submitted_from == sample_registration.submitted_from
            assert not player.is_builtin
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_player_database_error(self, db_service, sample_registration):
        """Test player creation with database error."""
        with patch.object(db_service, '_session_factory') as mock_session_factory:
            mock_session_factory.side_effect = Exception("Database connection failed")

            with pytest.raises(DatabaseError) as exc_info:
                await db_service.create_player(sample_registration)

            assert "Failed to create player" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_player_success(self, db_service):
        """Test successful player retrieval."""
        player_id = "test-player-id"
        
        with patch.object(db_service, '_session_factory') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            
            # Mock database query result
            mock_result = AsyncMock()
            mock_player_db = AsyncMock()
            mock_player_db.player_id = player_id
            mock_player_db.player_name = "TestPlayer"
            mock_player_db.submitted_from = "online"
            mock_player_db.sprite_path = None
            mock_player_db.minion_sprite_path = None
            mock_player_db.total_matches = 5
            mock_player_db.wins = 3
            mock_player_db.losses = 2
            mock_player_db.draws = 0
            mock_player_db.created_at = datetime.now()
            mock_player_db.is_builtin = False
            
            mock_result.scalar_one_or_none.return_value = mock_player_db
            mock_session.execute.return_value = mock_result

            player = await db_service.get_player(player_id)

            assert player is not None
            assert player.player_id == player_id
            assert player.player_name == "TestPlayer"
            assert player.total_matches == 5
            assert player.wins == 3

    @pytest.mark.asyncio
    async def test_get_player_not_found(self, db_service):
        """Test player retrieval when player doesn't exist."""
        player_id = "nonexistent-player"
        
        with patch.object(db_service, '_session_factory') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            player = await db_service.get_player(player_id)

            assert player is None

    @pytest.mark.asyncio
    async def test_update_player_stats_success(self, db_service):
        """Test successful player statistics update."""
        player_id = "test-player-id"
        game_result = GameResult(
            session_id="test-session",
            winner=player_id,
            loser="other-player",
            result_type=GameResultType.WIN,
            total_rounds=10,
            first_player=player_id,
            game_duration=300.0,
            final_scores={},
            end_condition="hp_zero",
            created_at=datetime.now()
        )
        
        with patch.object(db_service, '_session_factory') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            
            # Mock player found in database
            mock_result = AsyncMock()
            mock_player_db = AsyncMock()
            mock_player_db.total_matches = 0
            mock_player_db.wins = 0
            mock_player_db.losses = 0
            mock_player_db.draws = 0
            
            mock_result.scalar_one_or_none.return_value = mock_player_db
            mock_session.execute.return_value = mock_result
            mock_session.commit = AsyncMock()

            await db_service.update_player_stats(player_id, game_result)

            # Verify stats were updated correctly
            assert mock_player_db.total_matches == 1
            assert mock_player_db.wins == 1
            assert mock_player_db.losses == 0
            assert mock_player_db.draws == 0
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_player_stats_player_not_found(self, db_service):
        """Test player stats update when player doesn't exist."""
        player_id = "nonexistent-player"
        game_result = GameResult(
            session_id="test-session",
            winner=player_id,
            loser=None,
            result_type=GameResultType.WIN,
            total_rounds=10,
            first_player=player_id,
            game_duration=300.0,
            final_scores={},
            end_condition="hp_zero",
            created_at=datetime.now()
        )
        
        with patch.object(db_service, '_session_factory') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            with pytest.raises(PlayerNotFoundError):
                await db_service.update_player_stats(player_id, game_result)

    @pytest.mark.asyncio
    async def test_list_all_players(self, db_service):
        """Test listing all players."""
        with patch.object(db_service, '_session_factory') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            
            # Mock multiple players
            mock_player1 = AsyncMock()
            mock_player1.player_id = "player1"
            mock_player1.player_name = "Player 1"
            mock_player1.submitted_from = "online"
            mock_player1.sprite_path = None
            mock_player1.minion_sprite_path = None
            mock_player1.total_matches = 0
            mock_player1.wins = 0
            mock_player1.losses = 0
            mock_player1.draws = 0
            mock_player1.created_at = datetime.now()
            mock_player1.is_builtin = False
            
            mock_player2 = AsyncMock()
            mock_player2.player_id = "builtin_sample_1"
            mock_player2.player_name = "Sample Bot 1"
            mock_player2.submitted_from = "builtin"
            mock_player2.sprite_path = "assets/wizards/sample_bot1.png"
            mock_player2.minion_sprite_path = "assets/minions/minion_1.png"
            mock_player2.total_matches = 0
            mock_player2.wins = 0
            mock_player2.losses = 0
            mock_player2.draws = 0
            mock_player2.created_at = datetime.now()
            mock_player2.is_builtin = True
            
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = [mock_player1, mock_player2]
            mock_session.execute.return_value = mock_result

            players = await db_service.list_all_players(include_builtin=True)

            assert len(players) == 2
            assert players[0].player_id == "player1"
            assert players[1].player_id == "builtin_sample_1"
            assert not players[0].is_builtin
            assert players[1].is_builtin


class TestPlayerRegistry:
    """Test player registry functionality."""

    @pytest.fixture
    async def mock_db_service(self):
        """Create mock database service."""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    async def player_registry(self, mock_db_service):
        """Create player registry with mock database."""
        registry = PlayerRegistry(mock_db_service)
        # Mock initialization to avoid actual database calls
        with patch.object(registry, '_register_builtin_players', new_callable=AsyncMock):
            await registry.initialize()
        return registry

    @pytest.fixture
    def sample_registration(self):
        """Sample player registration data."""
        return PlayerRegistration(
            player_name="TestPlayer",
            submitted_from="online"
        )

    @pytest.mark.asyncio
    async def test_register_player_success(self, player_registry, mock_db_service, sample_registration):
        """Test successful player registration."""
        expected_player = Player(
            player_id="test-uuid",
            player_name=sample_registration.player_name,
            submitted_from=sample_registration.submitted_from,
            created_at=datetime.now(),
            is_builtin=False
        )
        
        mock_db_service.list_all_players.return_value = []
        mock_db_service.create_player.return_value = expected_player

        player = await player_registry.register_player(sample_registration)

        assert player.player_id == "test-uuid"
        assert player.player_name == sample_registration.player_name
        mock_db_service.create_player.assert_called_once_with(sample_registration)

    @pytest.mark.asyncio
    async def test_register_player_empty_name(self, player_registry, sample_registration):
        """Test player registration with empty name."""
        sample_registration.player_name = ""

        with pytest.raises(PlayerRegistrationError) as exc_info:
            await player_registry.register_player(sample_registration)

        assert "Player name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_player_database_error(self, player_registry, mock_db_service, sample_registration):
        """Test player registration with database error."""
        mock_db_service.list_all_players.return_value = []
        mock_db_service.create_player.side_effect = DatabaseError("Database connection failed")

        with pytest.raises(PlayerRegistrationError):
            await player_registry.register_player(sample_registration)

    @pytest.mark.asyncio
    async def test_get_player_success(self, player_registry, mock_db_service):
        """Test successful player retrieval."""
        player_id = "test-player-id"
        expected_player = Player(
            player_id=player_id,
            player_name="TestPlayer",
            submitted_from="online",
            created_at=datetime.now(),
            is_builtin=False
        )
        
        mock_db_service.get_player.return_value = expected_player

        player = await player_registry.get_player(player_id)

        assert player is not None
        assert player.player_id == player_id
        mock_db_service.get_player.assert_called_once_with(player_id)

    @pytest.mark.asyncio
    async def test_get_player_not_found(self, player_registry, mock_db_service):
        """Test player retrieval when not found."""
        player_id = "nonexistent-player"
        mock_db_service.get_player.return_value = None

        player = await player_registry.get_player(player_id)

        assert player is None

    @pytest.mark.asyncio
    async def test_get_player_or_raise_success(self, player_registry, mock_db_service):
        """Test get_player_or_raise with existing player."""
        player_id = "test-player-id"
        expected_player = Player(
            player_id=player_id,
            player_name="TestPlayer",
            submitted_from="online",
            created_at=datetime.now(),
            is_builtin=False
        )
        
        mock_db_service.get_player.return_value = expected_player

        player = await player_registry.get_player_or_raise(player_id)

        assert player.player_id == player_id

    @pytest.mark.asyncio
    async def test_get_player_or_raise_not_found(self, player_registry, mock_db_service):
        """Test get_player_or_raise with non-existent player."""
        player_id = "nonexistent-player"
        mock_db_service.get_player.return_value = None

        with pytest.raises(PlayerNotFoundError):
            await player_registry.get_player_or_raise(player_id)

    @pytest.mark.asyncio
    async def test_list_builtin_players(self, player_registry):
        """Test listing built-in players."""
        # Set up built-in players cache
        builtin_player = Player(
            player_id="builtin_sample_1",
            player_name="Sample Bot 1",
            submitted_from="builtin",
            is_builtin=True,
            created_at=datetime.now()
        )
        player_registry._builtin_players_cache = {"builtin_sample_1": builtin_player}

        players = await player_registry.list_builtin_players()

        assert len(players) >= 1
        # Should either return from database or cache

    @pytest.mark.asyncio
    async def test_validate_player_exists(self, player_registry, mock_db_service):
        """Test player existence validation."""
        player_id = "test-player-id"
        expected_player = Player(
            player_id=player_id,
            player_name="TestPlayer",
            submitted_from="online",
            created_at=datetime.now(),
            is_builtin=False
        )
        
        mock_db_service.get_player.return_value = expected_player

        exists = await player_registry.validate_player_exists(player_id)

        assert exists is True

    @pytest.mark.asyncio
    async def test_validate_player_not_exists(self, player_registry, mock_db_service):
        """Test player existence validation for non-existent player."""
        player_id = "nonexistent-player"
        mock_db_service.get_player.return_value = None

        exists = await player_registry.validate_player_exists(player_id)

        assert exists is False


class TestPlayerAPI:
    """Test player API endpoints."""

    @pytest.fixture
    def sample_registration(self):
        """Sample player registration data."""
        return {
            "player_name": "TestPlayer",
            "submitted_from": "online",
            "sprite_path": "assets/wizards/test.png"
        }

    @pytest.mark.asyncio
    async def test_register_player_endpoint_success(self, async_client, sample_registration):
        """Test successful player registration endpoint."""
        response = await async_client.post("/players/register", json=sample_registration)

        assert response.status_code == 201
        data = response.json()
        assert data["player_name"] == sample_registration["player_name"]
        assert data["submitted_from"] == sample_registration["submitted_from"]
        assert "player_id" in data
        assert data["is_builtin"] is False

    @pytest.mark.asyncio
    async def test_register_player_endpoint_validation_error(self, async_client):
        """Test player registration with validation errors."""
        invalid_registration = {
            "player_name": "",  # Empty name should fail
            "submitted_from": "online"
        }

        response = await async_client.post("/players/register", json=invalid_registration)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_player_endpoint_missing_field(self, async_client):
        """Test player registration with missing required field."""
        invalid_registration = {
            "submitted_from": "online"
            # Missing player_name
        }

        response = await async_client.post("/players/register", json=invalid_registration)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_player_endpoint_success(self, async_client, sample_registration):
        """Test successful player retrieval endpoint."""
        # First register a player
        register_response = await async_client.post("/players/register", json=sample_registration)
        assert register_response.status_code == 201
        player_data = register_response.json()
        player_id = player_data["player_id"]

        # Then retrieve the player
        response = await async_client.get(f"/players/{player_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == player_id
        assert data["player_name"] == sample_registration["player_name"]

    @pytest.mark.asyncio
    async def test_get_player_endpoint_not_found(self, async_client):
        """Test player retrieval with non-existent player ID."""
        nonexistent_id = "nonexistent-player-id"

        response = await async_client.get(f"/players/{nonexistent_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "PLAYER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_players_endpoint(self, async_client):
        """Test listing players endpoint."""
        response = await async_client.get("/players")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include built-in players by default

    @pytest.mark.asyncio
    async def test_list_players_endpoint_exclude_builtin(self, async_client, sample_registration):
        """Test listing players without built-in players."""
        # Register a user player first
        await async_client.post("/players/register", json=sample_registration)

        response = await async_client.get("/players?include_builtin=false")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should contain at least the registered player
        user_players = [p for p in data if not p["is_builtin"]]
        assert len(user_players) >= 1

    @pytest.mark.asyncio
    async def test_list_builtin_players_endpoint(self, async_client):
        """Test listing built-in players endpoint."""
        response = await async_client.get("/players/builtin/list")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should contain built-in players
        if data:
            for player in data:
                assert player["is_builtin"] is True

    @pytest.mark.asyncio
    async def test_player_statistics_endpoint(self, async_client):
        """Test player statistics endpoint."""
        response = await async_client.get("/players/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_players" in data
        assert "user_players" in data
        assert "builtin_players" in data
        assert isinstance(data["total_players"], int)


class TestPlayerManagementIntegration:
    """Integration tests for complete player management workflow."""

    @pytest.mark.asyncio
    async def test_complete_player_lifecycle(self, async_client):
        """Test complete player lifecycle: register -> retrieve -> list."""
        # 1. Register a new player
        registration_data = {
            "player_name": "IntegrationTestPlayer",
            "submitted_from": "online",
            "sprite_path": "assets/wizards/integration_test.png"
        }

        register_response = await async_client.post("/players/register", json=registration_data)
        assert register_response.status_code == 201
        
        player_data = register_response.json()
        player_id = player_data["player_id"]
        assert player_data["player_name"] == registration_data["player_name"]

        # 2. Retrieve the registered player
        get_response = await async_client.get(f"/players/{player_id}")
        assert get_response.status_code == 200
        
        retrieved_player = get_response.json()
        assert retrieved_player["player_id"] == player_id
        assert retrieved_player["player_name"] == registration_data["player_name"]

        # 3. Verify player appears in player list
        list_response = await async_client.get("/players")
        assert list_response.status_code == 200
        
        all_players = list_response.json()
        player_ids = [p["player_id"] for p in all_players]
        assert player_id in player_ids

        # 4. Verify player appears in user players list (excluding built-in)
        user_list_response = await async_client.get("/players?include_builtin=false")
        assert user_list_response.status_code == 200
        
        user_players = user_list_response.json()
        user_player_ids = [p["player_id"] for p in user_players]
        assert player_id in user_player_ids

        # 5. Verify statistics include the new player
        stats_response = await async_client.get("/players/stats/summary")
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert stats["user_players"] >= 1
        assert stats["total_players"] >= stats["user_players"]

    @pytest.mark.asyncio
    async def test_builtin_players_available(self, async_client):
        """Test that built-in players are available after initialization."""
        # Get built-in players
        builtin_response = await async_client.get("/players/builtin/list")
        assert builtin_response.status_code == 200
        
        builtin_players = builtin_response.json()
        assert len(builtin_players) > 0
        
        # Verify all are marked as built-in
        for player in builtin_players:
            assert player["is_builtin"] is True
            assert player["submitted_from"] == "builtin"
        
        # Verify built-in players are accessible individually
        for player in builtin_players[:2]:  # Test first 2 to avoid too many requests
            get_response = await async_client.get(f"/players/{player['player_id']}")
            assert get_response.status_code == 200
            
            player_detail = get_response.json()
            assert player_detail["player_id"] == player["player_id"]
            assert player_detail["is_builtin"] is True

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, async_client):
        """Test error handling in various scenarios."""
        # Test invalid registration data
        invalid_data = {"submitted_from": "online"}  # Missing player_name
        response = await async_client.post("/players/register", json=invalid_data)
        assert response.status_code == 422
        
        # Test retrieving non-existent player
        response = await async_client.get("/players/invalid-player-id")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"]["error"] == "PLAYER_NOT_FOUND" 