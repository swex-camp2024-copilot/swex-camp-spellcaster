"""Unit tests for all data models in the Spellcasters Playground Backend."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.models.actions import (
    Move,
    MoveHistory,
    MoveResult,
    PlayerAction,
    SpellAction,
    TurnActionCollection,
)
from backend.app.models.database import GameResultDB, PlayerDB, SessionDB
from backend.app.models.errors import (
    ErrorResponse,
    RateLimitErrorResponse,
    TimeoutErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from backend.app.models.events import (
    SSEConnection,
    GameOverEvent,
    HeartbeatEvent,
    TurnEvent,
)
from backend.app.models.players import Player, PlayerConfig, PlayerRegistration
from backend.app.models.results import GameResult, GameResultType, PlayerGameStats
from backend.app.models.sessions import GameState, PlayerSlot, SessionCreationRequest, TurnStatus


class TestPlayerModels:
    """Test player-related models."""

    def test_player_registration_valid(self):
        """Test valid player registration."""
        registration = PlayerRegistration(
            player_name="TestPlayer", submitted_from="online", sprite_path="assets/wizards/test.png"
        )
        assert registration.player_name == "TestPlayer"
        assert registration.submitted_from == "online"
        assert registration.sprite_path == "assets/wizards/test.png"

    def test_player_registration_defaults(self):
        """Test player registration with defaults."""
        registration = PlayerRegistration(player_name="TestPlayer")
        assert registration.submitted_from == "online"
        assert registration.sprite_path is None
        assert registration.minion_sprite_path is None

    def test_player_registration_validation(self):
        """Test player registration validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            PlayerRegistration(player_name="")

        # Too long name should fail
        with pytest.raises(ValidationError):
            PlayerRegistration(player_name="x" * 51)

        # Invalid submitted_from should fail
        with pytest.raises(ValidationError):
            PlayerRegistration(player_name="Test", submitted_from="invalid")

    def test_player_model(self):
        """Test player model."""
        player = Player(
            player_id=str(uuid4()),
            player_name="TestPlayer",
            submitted_from="online",
            total_matches=10,
            wins=7,
            losses=2,
            draws=1,
        )

        assert player.win_rate == 70.0
        assert not player.is_builtin

    def test_player_stats_update(self):
        """Test player statistics updates."""
        player = Player(player_id=str(uuid4()), player_name="TestPlayer", submitted_from="online")

        # Test win
        player.update_stats("win")
        assert player.total_matches == 1
        assert player.wins == 1
        assert player.losses == 0
        assert player.draws == 0

        # Test loss
        player.update_stats("loss")
        assert player.total_matches == 2
        assert player.wins == 1
        assert player.losses == 1

        # Test draw
        player.update_stats("draw")
        assert player.total_matches == 3
        assert player.draws == 1

    def test_player_config(self):
        """Test player configuration model."""
        config = PlayerConfig(player_id=str(uuid4()), bot_type="builtin", bot_id="sample_bot_1", is_human=False)
        assert config.bot_type == "builtin"
        assert config.bot_id == "sample_bot_1"
        assert not config.is_human


class TestSessionModels:
    """Test session-related models."""

    def test_player_slot(self):
        """Test player slot model."""
        slot = PlayerSlot(
            player_id=str(uuid4()), player_name="TestPlayer", is_builtin_bot=False, hp=100, mana=50, position=[5, 5]
        )
        assert slot.player_name == "TestPlayer"
        assert not slot.is_builtin_bot
        assert slot.hp == 100
        assert slot.position == [5, 5]

    def test_game_state(self):
        """Test game state model."""
        player1_id = str(uuid4())
        player2_id = str(uuid4())
        session_id = str(uuid4())

        slot1 = PlayerSlot(player_id=player1_id, player_name="Player1")
        slot2 = PlayerSlot(player_id=player2_id, player_name="Player2")

        game_state = GameState(session_id=session_id, player_1=slot1, player_2=slot2)

        assert game_state.session_id == session_id
        assert game_state.status == TurnStatus.WAITING
        assert game_state.turn_index == 0
        assert len(game_state.match_log) == 0

    def test_game_state_methods(self):
        """Test game state utility methods."""
        player1_id = str(uuid4())
        player2_id = str(uuid4())

        slot1 = PlayerSlot(player_id=player1_id, player_name="Player1")
        slot2 = PlayerSlot(player_id=player2_id, player_name="Player2")

        game_state = GameState(session_id=str(uuid4()), player_1=slot1, player_2=slot2)

        # Test get_player_slot
        assert game_state.get_player_slot(player1_id) == slot1
        assert game_state.get_player_slot(player2_id) == slot2
        assert game_state.get_player_slot("nonexistent") is None

        # Test get_opponent_slot
        assert game_state.get_opponent_slot(player1_id) == slot2
        assert game_state.get_opponent_slot(player2_id) == slot1

        # Test log entry
        game_state.add_log_entry("Test message")
        assert len(game_state.match_log) == 1
        assert "Test message" in game_state.match_log[0]

    def test_turn_status_enum(self):
        """Test turn status enumeration."""
        assert TurnStatus.WAITING == "waiting"
        assert TurnStatus.ACTIVE == "active"
        assert TurnStatus.COMPLETED == "completed"
        assert TurnStatus.CANCELLED == "cancelled"

    def test_session_creation_request_defaults(self):
        """Test session creation request with default visualize value."""
        request = SessionCreationRequest(
            player_1_config={"bot_type": "builtin", "bot_id": "sample_bot_1"},
            player_2_config={"bot_type": "builtin", "bot_id": "sample_bot_2"},
        )

        assert request.visualize is False  # Should default to False
        assert request.player_1_config["bot_type"] == "builtin"
        assert request.player_2_config["bot_type"] == "builtin"
        assert request.settings is None

    def test_session_creation_request_with_visualize(self):
        """Test session creation request with visualize enabled."""
        request = SessionCreationRequest(
            player_1_config={"bot_type": "builtin", "bot_id": "sample_bot_1"},
            player_2_config={"bot_type": "builtin", "bot_id": "sample_bot_2"},
            visualize=True,
        )

        assert request.visualize is True

    def test_session_creation_request_validation(self):
        """Test session creation request validation."""
        # Should accept boolean values
        request_true = SessionCreationRequest(
            player_1_config={"bot_type": "builtin"}, player_2_config={"bot_type": "builtin"}, visualize=True
        )
        assert request_true.visualize is True

        request_false = SessionCreationRequest(
            player_1_config={"bot_type": "builtin"}, player_2_config={"bot_type": "builtin"}, visualize=False
        )
        assert request_false.visualize is False


class TestEventModels:
    """Test SSE event models."""

    def test_turn_event(self):
        """Test SSE turn event."""
        event = TurnEvent(
            turn=5,
            game_state={"player1_hp": 80, "player2_hp": 90},
            actions=[{"player": "1", "action": "move"}],
            events=["Player 1 moved north"],
            log_line="Turn 5: Player 1 moved north",
        )

        assert event.event == "turn_update"
        assert event.turn == 5
        assert event.game_state["player1_hp"] == 80
        assert len(event.actions) == 1
        assert len(event.events) == 1

    def test_game_over_event(self):
        """Test SSE game over event."""
        event = GameOverEvent(
            winner="player1",
            winner_name="TestPlayer1",
            final_state={"player1_hp": 50, "player2_hp": 0},
            game_result={"result": "win", "duration": 300},
        )

        assert event.event == "game_over"
        assert event.winner == "player1"
        assert event.final_state["player2_hp"] == 0

    def test_heartbeat_event(self):
        """Test SSE heartbeat event."""
        event = HeartbeatEvent()
        assert event.event == "heartbeat"
        assert isinstance(event.timestamp, datetime)

    def test_sse_connection(self):
        """Test SSE connection model."""
        connection = SSEConnection(connection_id=str(uuid4()), session_id=str(uuid4()), player_id=str(uuid4()))

        assert connection.connection_id
        assert connection.session_id
        assert connection.player_id

        # Test ping update
        old_ping = connection.last_ping
        connection.update_ping()
        assert connection.last_ping > old_ping

        # Test stale check
        assert not connection.is_stale(timeout_seconds=60.0)


class TestActionModels:
    """Test action-related models."""

    def test_spell_action(self):
        """Test spell action model."""
        spell = SpellAction(name="fireball", target=[5, 3])
        assert spell.name == "fireball"
        assert spell.target == [5, 3]

        # Test spell without target
        heal_spell = SpellAction(name="heal")
        assert heal_spell.name == "heal"
        assert heal_spell.target is None

    def test_move_result(self):
        """Test move result model."""
        result = MoveResult(
            success=True,
            damage_dealt=15,
            damage_received=5,
            position_after=[6, 4],
            events=["Fireball hit!", "Took damage"],
            mana_used=20,
            hp_after=85,
            mana_after=30,
        )

        assert result.success
        assert result.damage_dealt == 15
        assert result.position_after == [6, 4]
        assert len(result.events) == 2

    def test_move(self):
        """Test move model."""
        spell = SpellAction(name="fireball", target=[5, 3])
        move = Move(player_id=str(uuid4()), turn=3, move=[1, 0], spell=spell)

        assert move.turn == 3
        assert move.move == [1, 0]
        assert move.spell.name == "fireball"
        assert move.result is None  # Not set until processed

    def test_player_action_conversion(self):
        """Test player action to move conversion."""
        player_id = str(uuid4())
        action = PlayerAction(
            player_id=player_id, turn=5, action_data={"move": [0, 1], "spell": {"name": "heal", "target": None}}
        )

        move = action.to_move()
        assert move.player_id == player_id
        assert move.turn == 5
        assert move.move == [0, 1]
        assert move.spell.name == "heal"

    def test_move_history(self):
        """Test move history model."""
        history = MoveHistory(session_id=str(uuid4()))

        # Add some moves
        move1 = Move(player_id="p1", turn=1, move=[1, 0])
        move2 = Move(player_id="p2", turn=1, move=[-1, 0])
        move3 = Move(player_id="p1", turn=2, move=[0, 1])

        history.add_move(move1)
        history.add_move(move2)
        history.add_move(move3)

        assert history.total_turns == 2
        assert len(history.moves) == 3

        # Test filtering methods
        p1_moves = history.get_moves_by_player("p1")
        assert len(p1_moves) == 2

        turn1_moves = history.get_moves_by_turn(1)
        assert len(turn1_moves) == 2

        last_turn = history.get_last_turn_moves()
        assert len(last_turn) == 1
        assert last_turn[0].turn == 2

    def test_turn_action_collection(self):
        """Test turn action collection."""
        collection = TurnActionCollection(turn=5)

        move1 = Move(player_id="p1", turn=5, move=[1, 0])
        move2 = Move(player_id="p2", turn=5, move=[-1, 0])

        collection.add_action("p1", move1)
        collection.add_action("p2", move2)

        expected_players = ["p1", "p2"]
        assert collection.is_complete(expected_players)
        assert len(collection.get_missing_players(expected_players)) == 0

        # Test incomplete collection
        collection2 = TurnActionCollection(turn=6)
        collection2.add_action("p1", move1)

        assert not collection2.is_complete(expected_players)
        missing = collection2.get_missing_players(expected_players)
        assert missing == ["p2"]


class TestResultModels:
    """Test result-related models."""

    def test_player_game_stats(self):
        """Test player game statistics."""
        stats = PlayerGameStats(
            player_id=str(uuid4()),
            player_name="TestPlayer",
            final_hp=75,
            final_mana=25,
            final_position=[3, 4],
            damage_dealt=50,
            damage_received=25,
            spells_cast=3,
            artifacts_collected=2,
            turns_played=15,
        )

        assert stats.final_hp == 75
        assert stats.survived  # HP > 0
        assert stats.damage_dealt == 50
        assert stats.spells_cast == 3

    def test_game_result(self):
        """Test game result model."""
        player1_id = str(uuid4())
        player2_id = str(uuid4())
        session_id = str(uuid4())

        stats1 = PlayerGameStats(
            player_id=player1_id,
            player_name="Player1",
            final_hp=75,
            final_mana=25,
            final_position=[3, 4],
            turns_played=15,
        )

        stats2 = PlayerGameStats(
            player_id=player2_id,
            player_name="Player2",
            final_hp=0,
            final_mana=10,
            final_position=[5, 2],
            turns_played=15,
        )

        result = GameResult(
            session_id=session_id,
            winner=player1_id,
            loser=player2_id,
            result_type=GameResultType.WIN,
            total_rounds=15,
            first_player=player1_id,
            game_duration=300.5,
            final_scores={player1_id: stats1, player2_id: stats2},
            end_condition="hp_zero",
        )

        assert result.winner == player1_id
        assert result.result_type == GameResultType.WIN
        assert result.game_duration == 300.5

        # Test utility methods
        winner_stats = result.get_winner_stats()
        assert winner_stats.player_id == player1_id
        assert winner_stats.final_hp == 75

        loser_stats = result.get_loser_stats()
        assert loser_stats.player_id == player2_id
        assert loser_stats.final_hp == 0

        # Test result determination
        assert result.determine_result_for_player(player1_id) == GameResultType.WIN
        assert result.determine_result_for_player(player2_id) == GameResultType.LOSS

    def test_game_result_type_enum(self):
        """Test game result type enumeration."""
        assert GameResultType.WIN == "win"
        assert GameResultType.LOSS == "loss"
        assert GameResultType.DRAW == "draw"


class TestDatabaseModels:
    """Test database models."""

    def test_player_db(self):
        """Test player database model."""
        player = PlayerDB(
            player_id=str(uuid4()),
            player_name="TestPlayer",
            submitted_from="online",
            total_matches=5,
            wins=3,
            losses=1,
            draws=1,
        )

        assert player.win_rate == 60.0
        assert not player.is_builtin

    def test_session_db(self):
        """Test session database model."""
        session = SessionDB(
            session_id=str(uuid4()), player_1_id=str(uuid4()), player_2_id=str(uuid4()), status="active", turn_index=5
        )

        assert session.status == "active"
        assert session.turn_index == 5
        assert session.duration_minutes is not None  # Should calculate duration

    def test_game_result_db(self):
        """Test game result database model."""
        result = GameResultDB(
            session_id=str(uuid4()),
            winner_id=str(uuid4()),
            loser_id=str(uuid4()),
            result_type="win",
            total_rounds=20,
            game_duration=450.0,
            end_condition="hp_zero",
            player_1_final_hp=60,
            player_1_final_mana=0,
            player_2_final_hp=0,
            player_2_final_mana=15,
        )

        assert result.result_type == "win"
        assert result.total_rounds == 20
        assert result.player_1_final_hp == 60


class TestErrorModels:
    """Test error response models."""

    def test_error_response(self):
        """Test basic error response."""
        error = ErrorResponse(
            error="SESSION_NOT_FOUND",
            message="Session abc123 not found",
            session_id="abc123",
            details={"attempted_id": "abc123"},
        )

        assert error.error == "SESSION_NOT_FOUND"
        assert error.message == "Session abc123 not found"
        assert error.session_id == "abc123"
        assert error.details["attempted_id"] == "abc123"

    def test_validation_error_response(self):
        """Test validation error response."""
        error_detail = ValidationErrorDetail(field="player_name", message="Field is required", invalid_value=None)

        validation_error = ValidationErrorResponse(
            error="VALIDATION_ERROR", message="Request validation failed", validation_errors=[error_detail]
        )

        assert validation_error.error == "VALIDATION_ERROR"
        assert len(validation_error.validation_errors) == 1
        assert validation_error.validation_errors[0].field == "player_name"

    def test_timeout_error_response(self):
        """Test timeout error response."""
        timeout_error = TimeoutErrorResponse(
            error="BOT_TIMEOUT", message="Bot execution timed out", timeout_seconds=5.0, operation="bot_decision"
        )

        assert timeout_error.timeout_seconds == 5.0
        assert timeout_error.operation == "bot_decision"

    def test_rate_limit_error_response(self):
        """Test rate limit error response."""
        rate_limit_error = RateLimitErrorResponse(
            error="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            retry_after_seconds=60,
            limit_type="action_submission",
        )

        assert rate_limit_error.retry_after_seconds == 60
        assert rate_limit_error.limit_type == "action_submission"


# Test fixtures for integration tests
@pytest.fixture
def sample_player():
    """Create a sample player for testing."""
    return Player(player_id=str(uuid4()), player_name="TestPlayer", submitted_from="online")


@pytest.fixture
def sample_game_state():
    """Create a sample game state for testing."""
    slot1 = PlayerSlot(player_id=str(uuid4()), player_name="Player1")
    slot2 = PlayerSlot(player_id=str(uuid4()), player_name="Player2")

    return GameState(session_id=str(uuid4()), player_1=slot1, player_2=slot2)


@pytest.fixture
def sample_move():
    """Create a sample move for testing."""
    return Move(player_id=str(uuid4()), turn=1, move=[1, 0], spell=SpellAction(name="fireball", target=[5, 3]))


class TestConfigurationSettings:
    """Test configuration settings."""

    def test_visualization_config_defaults(self):
        """Test that visualization config options have correct defaults."""
        from backend.app.core.config import settings

        # Test visualization config defaults
        assert settings.enable_visualization is True
        assert settings.max_visualized_sessions == 10
        assert settings.visualizer_queue_size == 100
        assert settings.visualizer_shutdown_timeout == 5.0

    def test_visualization_config_types(self):
        """Test that visualization config options have correct types."""
        from backend.app.core.config import settings

        assert isinstance(settings.enable_visualization, bool)
        assert isinstance(settings.max_visualized_sessions, int)
        assert isinstance(settings.visualizer_queue_size, int)
        assert isinstance(settings.visualizer_shutdown_timeout, float)
