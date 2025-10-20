"""Unit tests for client initialization."""

import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from client.bot_client import BotClient, RandomWalkStrategy
from client.bot_client_main import get_os_username, load_bot_class, parse_args


class TestOSUsernameDetection:
    """Tests for OS username detection."""

    def test_get_os_username_success(self):
        """Test successful username retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="testuser\n", stderr="")
            username = get_os_username()
            assert username == "testuser"
            mock_run.assert_called_once_with(["whoami"], capture_output=True, text=True, check=True, timeout=5)

    def test_get_os_username_empty(self):
        """Test error when whoami returns empty string."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", stderr="")
            with pytest.raises(RuntimeError, match="whoami returned empty username"):
                get_os_username()

    def test_get_os_username_command_failed(self):
        """Test error when whoami command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "whoami", stderr="command not found")
            with pytest.raises(RuntimeError, match="Failed to get OS username"):
                get_os_username()

    def test_get_os_username_timeout(self):
        """Test error when whoami command times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("whoami", 5)
            with pytest.raises(RuntimeError, match="whoami command timed out"):
                get_os_username()

    def test_get_os_username_not_found(self):
        """Test error when whoami command not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("whoami not found")
            with pytest.raises(RuntimeError, match="whoami command not found"):
                get_os_username()


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_parse_args_defaults(self, monkeypatch):
        """Test CLI argument parsing with all defaults."""
        # Clear environment variables
        for key in ["BASE_URL", "PLAYER_ID", "OPPONENT_ID", "BOT_TYPE", "BOT_PATH", "MAX_EVENTS", "LOG_LEVEL"]:
            monkeypatch.delenv(key, raising=False)

        with patch("sys.argv", ["bot_client_main.py"]):
            args = parse_args()
            assert args.base_url == "http://localhost:8000"
            assert args.player_id is None  # Should be None, will default to OS username in main()
            assert args.opponent_id == "builtin_sample_1"
            assert args.bot_type == "random"
            assert args.bot_path is None
            assert args.max_events == 100
            assert args.log_level == "INFO"

    def test_parse_args_with_arguments(self):
        """Test CLI argument parsing with explicit arguments."""
        with patch(
            "sys.argv",
            [
                "bot_client_main.py",
                "--base-url",
                "http://example.com:8080",
                "--player-id",
                "alice",
                "--opponent-id",
                "bob",
                "--bot-type",
                "custom",
                "--bot-path",
                "bots.sample_bot1.sample_bot_1.SampleBot1",
                "--max-events",
                "50",
                "--log-level",
                "DEBUG",
            ],
        ):
            args = parse_args()
            assert args.base_url == "http://example.com:8080"
            assert args.player_id == "alice"
            assert args.opponent_id == "bob"
            assert args.bot_type == "custom"
            assert args.bot_path == "bots.sample_bot1.sample_bot_1.SampleBot1"
            assert args.max_events == 50
            assert args.log_level == "DEBUG"

    def test_parse_args_environment_variables(self, monkeypatch):
        """Test CLI argument parsing with environment variables."""
        monkeypatch.setenv("BASE_URL", "http://env.example.com")
        monkeypatch.setenv("PLAYER_ID", "env_user")
        monkeypatch.setenv("OPPONENT_ID", "builtin_sample_2")
        monkeypatch.setenv("BOT_TYPE", "custom")
        monkeypatch.setenv("BOT_PATH", "bots.test.TestBot")
        monkeypatch.setenv("MAX_EVENTS", "200")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        with patch("sys.argv", ["bot_client_main.py"]):
            args = parse_args()
            assert args.base_url == "http://env.example.com"
            assert args.player_id == "env_user"
            assert args.opponent_id == "builtin_sample_2"
            assert args.bot_type == "custom"
            assert args.bot_path == "bots.test.TestBot"
            assert args.max_events == 200
            assert args.log_level == "WARNING"

    def test_parse_args_cli_overrides_env(self, monkeypatch):
        """Test that CLI arguments override environment variables."""
        monkeypatch.setenv("PLAYER_ID", "env_user")
        monkeypatch.setenv("OPPONENT_ID", "builtin_sample_2")

        with patch("sys.argv", ["bot_client_main.py", "--player-id", "cli_user", "--opponent-id", "builtin_sample_3"]):
            args = parse_args()
            assert args.player_id == "cli_user"
            assert args.opponent_id == "builtin_sample_3"


class TestBotLoading:
    """Tests for bot class loading."""

    def test_load_bot_class_invalid_format_single_part(self):
        """Test error when bot path has only one part."""
        with pytest.raises(ValueError, match="Invalid bot path.*Expected format: module.path.ClassName"):
            load_bot_class("InvalidPath")

    def test_load_bot_class_invalid_module(self):
        """Test error when module cannot be imported."""
        with pytest.raises(ImportError):
            load_bot_class("nonexistent.module.ClassName")

    def test_load_bot_class_invalid_class(self):
        """Test error when class cannot be found in module."""
        with pytest.raises(AttributeError):
            load_bot_class("client.bot_client.NonExistentClass")

    def test_load_bot_class_success(self):
        """Test successful bot class loading."""
        bot_class = load_bot_class("client.bot_client.RandomWalkStrategy")
        assert bot_class == RandomWalkStrategy
        assert hasattr(bot_class, "decide")
        assert hasattr(bot_class, "name")


class TestBotInstantiation:
    """Tests for bot instantiation."""

    def test_random_walk_strategy_has_name(self):
        """Test that RandomWalkStrategy has name property."""
        bot = RandomWalkStrategy()
        assert hasattr(bot, "name")
        assert bot.name == "RandomWalkStrategy"

    def test_random_walk_strategy_has_decide(self):
        """Test that RandomWalkStrategy has decide method."""
        bot = RandomWalkStrategy()
        assert hasattr(bot, "decide")
        assert callable(bot.decide)

    def test_random_walk_strategy_decide_signature(self):
        """Test that RandomWalkStrategy.decide has correct signature."""
        bot = RandomWalkStrategy()
        # Test with minimal state
        state = {"turn": 1, "self": {}, "opponent": {}, "artifacts": [], "minions": []}
        action = bot.decide(state)
        assert "move" in action
        assert "spell" in action
        assert isinstance(action["move"], list)
        assert len(action["move"]) == 2

    def test_random_walk_strategy_toggle_behavior(self):
        """Test that RandomWalkStrategy toggles movement."""
        bot = RandomWalkStrategy()
        state = {"turn": 1, "self": {}, "opponent": {}, "artifacts": [], "minions": []}

        action1 = bot.decide(state)
        action2 = bot.decide(state)

        # Toggle should flip the movement
        assert action1["move"][0] != action2["move"][0]


class TestBotClientInitialization:
    """Tests for BotClient initialization."""

    def test_bot_client_accepts_bot_instance(self):
        """Test that BotClient accepts bot instance in constructor."""
        bot = RandomWalkStrategy()
        client = BotClient("http://localhost:8000", bot_instance=bot)
        assert client.bot == bot
        assert client.base_url == "http://localhost:8000"

    def test_bot_client_strips_trailing_slash(self):
        """Test that BotClient strips trailing slash from base_url."""
        bot = RandomWalkStrategy()
        client = BotClient("http://localhost:8000/", bot_instance=bot)
        assert client.base_url == "http://localhost:8000"


class TestBotPathValidation:
    """Tests for bot path validation in run_bot."""

    def test_custom_bot_requires_bot_path(self):
        """Test that custom bot type requires bot_path."""
        from client.bot_client_main import run_bot

        with pytest.raises(ValueError, match="--bot-path is required when --bot-type=custom"):
            import asyncio

            asyncio.run(run_bot("http://localhost:8000", "user", "direct", "builtin_sample_1", 100, "custom", None))


class TestMatchCreation:
    """Tests for BotClient match creation."""

    @pytest.mark.asyncio
    async def test_start_match_with_builtin_opponent(self):
        """Test starting a match against a builtin bot."""
        from unittest.mock import AsyncMock

        import httpx

        bot = RandomWalkStrategy()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = Mock()
        mock_response.json.return_value = {"session_id": "test-session-123"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)
        session_id = await client.start_match("player1", "builtin_sample_1", visualize=False)

        assert session_id == "test-session-123"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:8000/playground/start"
        payload = call_args[1]["json"]
        assert payload["player_1_config"]["player_id"] == "player1"
        assert payload["player_1_config"]["bot_type"] == "player"
        assert payload["player_2_config"]["player_id"] == "builtin_sample_1"
        assert payload["player_2_config"]["bot_type"] == "builtin"
        assert payload["player_2_config"]["bot_id"] == "sample_bot_1"
        assert payload["visualize"] is False

    @pytest.mark.asyncio
    async def test_start_match_with_remote_player_opponent(self):
        """Test starting a match against a remote player."""
        from unittest.mock import AsyncMock

        import httpx

        bot = RandomWalkStrategy()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = Mock()
        mock_response.json.return_value = {"session_id": "test-session-456"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)
        session_id = await client.start_match("player1", "player2", visualize=True)

        assert session_id == "test-session-456"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:8000/playground/start"
        payload = call_args[1]["json"]
        assert payload["player_1_config"]["player_id"] == "player1"
        assert payload["player_1_config"]["bot_type"] == "player"
        assert payload["player_2_config"]["player_id"] == "player2"
        assert payload["player_2_config"]["bot_type"] == "player"
        assert "bot_id" not in payload["player_2_config"]
        assert payload["visualize"] is True

    @pytest.mark.asyncio
    async def test_opponent_type_detection_builtin_sample(self):
        """Test opponent type detection for builtin_sample_ bots."""
        from unittest.mock import AsyncMock

        import httpx

        bot = RandomWalkStrategy()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = Mock()
        mock_response.json.return_value = {"session_id": "test-session"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

        # Test builtin_sample_1 -> sample_bot_1
        await client.start_match("player1", "builtin_sample_1")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["player_2_config"]["bot_id"] == "sample_bot_1"

        # Test builtin_sample_2 -> sample_bot_2
        await client.start_match("player1", "builtin_sample_2")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["player_2_config"]["bot_id"] == "sample_bot_2"

    @pytest.mark.asyncio
    async def test_opponent_type_detection_builtin_other(self):
        """Test opponent type detection for non-sample builtin bots."""
        from unittest.mock import AsyncMock

        import httpx

        bot = RandomWalkStrategy()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = Mock()
        mock_response.json.return_value = {"session_id": "test-session"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        client = BotClient("http://localhost:8000", bot_instance=bot, http_client=mock_client)

        # Test builtin_tactical -> tactical_bot
        await client.start_match("player1", "builtin_tactical")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["player_2_config"]["bot_id"] == "tactical_bot"
