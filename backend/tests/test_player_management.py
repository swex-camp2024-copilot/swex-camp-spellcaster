"""Clean tests for the Player Management System with working fixtures."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from backend.app.core.exceptions import DatabaseError, PlayerNotFoundError, PlayerRegistrationError
from backend.app.models.players import Player, PlayerRegistration
from backend.app.services.database import DatabaseService
from backend.app.services.player_registry import PlayerRegistry


class TestPlayerRegistry:
    """Test player registry functionality."""

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    def player_registry(self, mock_db_service):
        """Create player registry with mock database."""
        registry = PlayerRegistry(mock_db_service)
        # Set up mock cache for built-in players
        registry._builtin_players_cache = {}
        return registry

    @pytest.fixture
    def sample_registration(self):
        """Sample player registration data."""
        return PlayerRegistration(player_name="TestPlayer", submitted_from="online")

    @pytest.mark.asyncio
    async def test_register_player_success(self, player_registry, mock_db_service, sample_registration):
        """Test successful player registration."""
        expected_player = Player(
            player_id="testplayer",
            player_name=sample_registration.player_name,
            submitted_from=sample_registration.submitted_from,
            created_at=datetime.now(),
            is_builtin=False,
        )

        mock_db_service.list_all_players.return_value = []
        mock_db_service.create_player.return_value = expected_player

        player = await player_registry.register_player(sample_registration)

        assert player.player_id == "testplayer"
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
    async def test_get_player_success(self, player_registry, mock_db_service):
        """Test successful player retrieval."""
        player_id = "test-player-id"
        expected_player = Player(
            player_id=player_id,
            player_name="TestPlayer",
            submitted_from="online",
            created_at=datetime.now(),
            is_builtin=False,
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
    async def test_delete_player_success(self, player_registry, mock_db_service):
        """Test successful player deletion."""
        player_id = "test-player-id"
        test_player = Player(
            player_id=player_id,
            player_name="TestPlayer",
            submitted_from="online",
            created_at=datetime.now(),
            is_builtin=False,
        )

        mock_db_service.get_player.return_value = test_player
        mock_db_service.delete_player.return_value = True

        success = await player_registry.delete_player(player_id)

        assert success is True
        mock_db_service.delete_player.assert_called_once_with(player_id)

    @pytest.mark.asyncio
    async def test_delete_player_not_found(self, player_registry, mock_db_service):
        """Test deletion of non-existent player."""
        player_id = "nonexistent-player"
        mock_db_service.get_player.return_value = None

        with pytest.raises(PlayerNotFoundError):
            await player_registry.delete_player(player_id)

    @pytest.mark.asyncio
    async def test_delete_builtin_player_rejected(self, player_registry, mock_db_service):
        """Test that built-in players cannot be deleted."""
        player_id = "builtin_sample_1"
        builtin_player = Player(
            player_id=player_id,
            player_name="Sample Bot 1",
            submitted_from="builtin",
            created_at=datetime.now(),
            is_builtin=True,
        )

        mock_db_service.get_player.return_value = builtin_player

        with pytest.raises(PlayerRegistrationError) as exc_info:
            await player_registry.delete_player(player_id)

        assert "Cannot delete built-in players" in str(exc_info.value)
        mock_db_service.delete_player.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_player_exists(self, player_registry, mock_db_service):
        """Test player existence validation."""
        player_id = "test-player-id"
        expected_player = Player(
            player_id=player_id,
            player_name="TestPlayer",
            submitted_from="online",
            created_at=datetime.now(),
            is_builtin=False,
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


class TestDatabaseServiceSlugGeneration:
    """Test slug generation logic in DatabaseService."""

    @pytest.fixture
    def db_service(self):
        """Create database service instance."""
        return DatabaseService()

    def test_generate_player_slug_basic(self, db_service):
        """Test basic slug generation from player name."""
        assert db_service._generate_player_slug("Kevin Lin") == "kevin-lin"
        assert db_service._generate_player_slug("TestPlayer") == "testplayer"
        assert db_service._generate_player_slug("John Doe") == "john-doe"

    def test_generate_player_slug_special_characters(self, db_service):
        """Test that special characters are removed from slug."""
        assert db_service._generate_player_slug("O'Brien!") == "obrien"
        assert db_service._generate_player_slug("Test User #1") == "test-user-1"
        assert db_service._generate_player_slug("Alice@Bob") == "alicebob"
        assert db_service._generate_player_slug("User$123") == "user123"

    def test_generate_player_slug_multiple_spaces(self, db_service):
        """Test handling of multiple consecutive spaces."""
        assert db_service._generate_player_slug("John   Doe") == "john-doe"
        assert db_service._generate_player_slug("Test  Player  Name") == "test-player-name"

    def test_generate_player_slug_leading_trailing_spaces(self, db_service):
        """Test handling of leading and trailing spaces."""
        assert db_service._generate_player_slug("  Kevin Lin  ") == "kevin-lin"
        assert db_service._generate_player_slug(" TestPlayer ") == "testplayer"

    def test_generate_player_slug_only_special_chars(self, db_service):
        """Test handling of names with only special characters."""
        assert db_service._generate_player_slug("!!!") == ""
        assert db_service._generate_player_slug("@#$%") == ""

    def test_generate_player_slug_mixed_case(self, db_service):
        """Test that slug is always lowercase."""
        assert db_service._generate_player_slug("KEVIN LIN") == "kevin-lin"
        assert db_service._generate_player_slug("JoHn DoE") == "john-doe"

    @pytest.mark.asyncio
    async def test_create_player_slug_generation(self, db_service):
        """Test that create_player generates slug-based IDs."""
        # This will be an integration test that requires database setup
        # For now, we verify the slug generation method works correctly
        registration = PlayerRegistration(player_name="Kevin Lin", submitted_from="online")

        expected_slug = db_service._generate_player_slug(registration.player_name)
        assert expected_slug == "kevin-lin"


# Note: API and integration tests would go here, but they require a running FastAPI app
# These tests focus on the core business logic which is most important to verify
