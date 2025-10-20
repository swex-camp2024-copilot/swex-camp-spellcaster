"""Tests for the bot system implementation."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from backend.app.models.bots import BotInterface, PlayerBot, PlayerBotFactory, BotCreationRequest, BotInfo
from backend.app.models.players import Player, PlayerRegistration
from backend.app.services.builtin_bots import BuiltinBotRegistry, BuiltinBotWrapper
from backend.app.services.game_adapter import GameEngineAdapter


class TestBotInterface:
    """Test the abstract BotInterface."""

    def test_bot_interface_properties(self):
        """Test that BotInterface correctly exposes player properties."""
        # Create a test player
        player = Player(
            player_id="test_player_123",
            player_name="Test Player",
            submitted_from="test",
            is_builtin=False,
            created_at=datetime.now(),
        )

        # Create a concrete implementation for testing
        class TestBot(BotInterface):
            def decide(self, state):
                return {"move": [0, 0], "spell": None}

        bot = TestBot(player)

        # Test properties
        assert bot.player == player
        assert bot.name == "Test Player"
        assert bot.player_id == "test_player_123"
        assert bot.is_builtin == False

    def test_bot_interface_requires_decide_implementation(self):
        """Test that BotInterface requires decide method implementation."""
        player = Player(player_id="test_player", player_name="Test", submitted_from="test", created_at=datetime.now())

        # This should fail because decide is not implemented
        with pytest.raises(TypeError):

            class IncompleteBot(BotInterface):
                pass

            IncompleteBot(player)


class TestPlayerBot:
    """Test the PlayerBot implementation (remote player action submission)."""

    def test_player_bot_creation(self):
        """Test PlayerBot creation."""
        player = Player(
            player_id="test_player", player_name="Test Player", submitted_from="online", created_at=datetime.now()
        )

        bot = PlayerBot(player)
        assert bot.player == player
        assert bot.name == "Test Player"
        assert bot._last_action is None

    def test_player_bot_decide_no_action(self):
        """Test PlayerBot decide method with no action submitted."""
        player = Player(
            player_id="test_player", player_name="Test Player", submitted_from="online", created_at=datetime.now()
        )

        bot = PlayerBot(player)

        # Should return default action when no action submitted
        state = {"self": {"hp": 100}, "opponent": {"hp": 100}}
        action = bot.decide(state)
        assert action == {"move": [0, 0], "spell": None}

    def test_player_bot_set_and_retrieve_action(self):
        """Test PlayerBot action storage and retrieval."""
        from backend.app.models.actions import ActionData

        player = Player(
            player_id="test_player", player_name="Test Player", submitted_from="online", created_at=datetime.now()
        )

        bot = PlayerBot(player)

        # Submit an action
        action_data = ActionData(move=[1, 0], spell=None)
        bot.set_action(action_data)

        # Should return submitted action
        state = {"self": {"hp": 100}, "opponent": {"hp": 100}}
        action = bot.decide(state)
        assert action["move"] == [1, 0]
        assert action["spell"] is None

    def test_player_bot_action_with_spell(self):
        """Test PlayerBot with spell action."""
        from backend.app.models.actions import ActionData

        player = Player(
            player_id="test_player", player_name="Test Player", submitted_from="online", created_at=datetime.now()
        )

        bot = PlayerBot(player)

        # Submit action with spell
        action_data = ActionData(move=[0, 0], spell={"name": "fireball", "target": [5, 5]})
        bot.set_action(action_data)

        # Should return submitted action with spell
        state = {"self": {"hp": 100}, "opponent": {"hp": 100}}
        action = bot.decide(state)
        assert action["move"] == [0, 0]
        assert action["spell"]["name"] == "fireball"
        assert action["spell"]["target"] == [5, 5]

    def test_player_bot_action_without_move(self):
        """Test PlayerBot when move is None."""
        from backend.app.models.actions import ActionData

        player = Player(
            player_id="test_player", player_name="Test Player", submitted_from="online", created_at=datetime.now()
        )

        bot = PlayerBot(player)

        # Submit action with no move
        action_data = ActionData(move=None, spell={"name": "shield"})
        bot.set_action(action_data)

        # Should default move to [0, 0]
        state = {"self": {"hp": 100}, "opponent": {"hp": 100}}
        action = bot.decide(state)
        assert action["move"] == [0, 0]
        assert action["spell"]["name"] == "shield"


class TestPlayerBotFactory:
    """Test the PlayerBotFactory (deprecated - kept for backward compatibility)."""

    def test_create_bot_with_existing_player(self):
        """Test creating bot with existing player ID."""
        # Mock player registry
        player = Player(
            player_id="existing_player",
            player_name="Existing Player",
            submitted_from="online",
            created_at=datetime.now(),
        )

        mock_registry = Mock()
        mock_registry.get_player.return_value = player

        # Note: bot_code parameter is deprecated but kept for backward compatibility
        request = BotCreationRequest(bot_code="# Remote player bot", player_id="existing_player")

        bot = PlayerBotFactory.create_bot(request, mock_registry)

        assert isinstance(bot, PlayerBot)
        assert bot.player == player
        mock_registry.get_player.assert_called_once_with("existing_player")

    def test_create_bot_with_new_player_registration(self):
        """Test creating bot with new player registration."""
        # Mock player registry
        new_player = Player(
            player_id="new_player_123", player_name="New Player", submitted_from="online", created_at=datetime.now()
        )

        mock_registry = Mock()
        mock_registry.register_player.return_value = new_player

        # Note: bot_code parameter is deprecated but kept for backward compatibility
        request = BotCreationRequest(
            bot_code="# Remote player bot",
            player_registration=PlayerRegistration(player_name="New Player", submitted_from="online"),
        )

        bot = PlayerBotFactory.create_bot(request, mock_registry)

        assert isinstance(bot, PlayerBot)
        assert bot.player == new_player
        mock_registry.register_player.assert_called_once()

    def test_create_bot_player_not_found(self):
        """Test creating bot with non-existent player ID."""
        mock_registry = Mock()
        mock_registry.get_player.return_value = None

        request = BotCreationRequest(bot_code="# Remote player bot", player_id="nonexistent_player")

        with pytest.raises(ValueError, match="Player nonexistent_player not found"):
            PlayerBotFactory.create_bot(request, mock_registry)

    def test_create_bot_no_player_info(self):
        """Test creating bot without player ID or registration."""
        mock_registry = Mock()

        request = BotCreationRequest(bot_code="# Remote player bot")

        with pytest.raises(ValueError, match="Must provide either player_id or player_registration"):
            PlayerBotFactory.create_bot(request, mock_registry)


class TestBuiltinBotRegistry:
    """Test the BuiltinBotRegistry."""

    def test_get_builtin_player(self):
        """Test getting built-in player."""
        player = BuiltinBotRegistry.get_builtin_player("builtin_sample_1")

        assert player.player_id == "builtin_sample_1"
        assert player.player_name == "Sample Bot 1"
        assert player.is_builtin == True

    def test_get_nonexistent_builtin_player(self):
        """Test getting non-existent built-in player."""
        with pytest.raises(ValueError, match="Built-in player nonexistent not found"):
            BuiltinBotRegistry.get_builtin_player("nonexistent")

    @patch("importlib.import_module")
    def test_create_builtin_bot(self, mock_import):
        """Test creating built-in bot."""
        # Mock the bot class
        mock_bot_class = Mock()
        mock_module = Mock()
        mock_module.SampleBot1 = mock_bot_class
        mock_import.return_value = mock_module

        bot = BuiltinBotRegistry.create_bot("sample_bot_1")

        assert isinstance(bot, BuiltinBotWrapper)
        assert bot.player.player_id == "builtin_sample_1"
        mock_import.assert_called_once_with("bots.sample_bot1.sample_bot_1")

    def test_create_nonexistent_builtin_bot(self):
        """Test creating non-existent built-in bot."""
        with pytest.raises(ValueError, match="Built-in bot nonexistent not found"):
            BuiltinBotRegistry.create_bot("nonexistent")

    def test_list_available_bots(self):
        """Test listing available built-in bots."""
        bots = BuiltinBotRegistry.list_available_bots()

        assert len(bots) > 0
        assert all(isinstance(bot, BotInfo) for bot in bots)
        assert all(bot.bot_type == "builtin" for bot in bots)

    def test_get_all_builtin_players(self):
        """Test getting all built-in players."""
        players = BuiltinBotRegistry.get_all_builtin_players()

        assert len(players) > 0
        assert all(isinstance(player, Player) for player in players)
        assert all(player.is_builtin for player in players)

    def test_is_builtin_bot(self):
        """Test checking if bot ID is built-in."""
        assert BuiltinBotRegistry.is_builtin_bot("sample_bot_1") == True
        assert BuiltinBotRegistry.is_builtin_bot("nonexistent") == False

    def test_is_builtin_player(self):
        """Test checking if player ID is built-in."""
        assert BuiltinBotRegistry.is_builtin_player("builtin_sample_1") == True
        assert BuiltinBotRegistry.is_builtin_player("user_player") == False


class TestBuiltinBotWrapper:
    """Test the BuiltinBotWrapper."""

    def test_wrapper_delegates_to_original_bot(self):
        """Test that wrapper correctly delegates to original bot."""
        # Create a mock original bot
        mock_original_bot = Mock()
        mock_original_bot.decide.return_value = {"move": [1, 1], "spell": {"name": "fireball"}}

        # Create a test player
        player = Player(
            player_id="test_player",
            player_name="Test Player",
            submitted_from="builtin",
            is_builtin=True,
            created_at=datetime.now(),
        )

        # Create wrapper
        wrapper = BuiltinBotWrapper(player, lambda: mock_original_bot)

        # Test decision delegation
        state = {"self": {"hp": 100}}
        action = wrapper.decide(state)

        assert action == {"move": [1, 1], "spell": {"name": "fireball"}}
        mock_original_bot.decide.assert_called_once_with(state)

    def test_wrapper_handles_original_bot_errors(self):
        """Test that wrapper handles errors from original bot."""
        # Create a mock original bot that raises an error
        mock_original_bot = Mock()
        mock_original_bot.decide.side_effect = Exception("Bot error!")

        player = Player(
            player_id="test_player",
            player_name="Test Player",
            submitted_from="builtin",
            is_builtin=True,
            created_at=datetime.now(),
        )

        wrapper = BuiltinBotWrapper(player, lambda: mock_original_bot)

        # Should return safe default action on error
        state = {"self": {"hp": 100}}
        action = wrapper.decide(state)

        assert action == {"move": [0, 0], "spell": None}


class TestGameEngineAdapter:
    """Test the GameEngineAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initialization."""
        adapter = GameEngineAdapter()

        assert adapter.engine is None
        assert adapter.bot1 is None
        assert adapter.bot2 is None
        assert adapter._game_started == False

    @patch("backend.app.services.game_adapter.GameEngine")
    def test_initialize_match(self, mock_game_engine):
        """Test match initialization."""
        # Create test bots
        player1 = Player(player_id="p1", player_name="Bot1", submitted_from="test", created_at=datetime.now())
        player2 = Player(player_id="p2", player_name="Bot2", submitted_from="test", created_at=datetime.now())

        class TestBot(BotInterface):
            def decide(self, state):
                return {"move": [0, 0]}

        bot1 = TestBot(player1)
        bot2 = TestBot(player2)

        adapter = GameEngineAdapter()
        adapter.initialize_match(bot1, bot2)

        assert adapter.bot1 == bot1
        assert adapter.bot2 == bot2
        assert adapter._game_started == True
        mock_game_engine.assert_called_once_with(bot1, bot2)

    def test_get_game_state_without_engine(self):
        """Test getting game state without initialized engine."""
        adapter = GameEngineAdapter()
        state = adapter.get_game_state()

        assert state == {}

    def test_check_game_over_without_engine(self):
        """Test checking game over without initialized engine."""
        adapter = GameEngineAdapter()
        result = adapter.check_game_over()

        assert result is None
