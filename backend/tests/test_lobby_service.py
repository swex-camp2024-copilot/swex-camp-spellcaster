"""Unit tests for LobbyService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.core.exceptions import PlayerAlreadyInLobbyError, PlayerNotFoundError
from backend.app.models.lobby import LobbyJoinRequest
from backend.app.models.players import Player, PlayerConfig
from backend.app.services.lobby_service import LobbyService


@pytest.fixture
def mock_db_service():
    """Mock DatabaseService for testing."""
    db = AsyncMock()

    # Mock player data
    player1 = Player(
        player_id="player-1",
        player_name="Player 1",
        submitted_from="online",
        is_builtin=False,
    )
    player2 = Player(
        player_id="player-2",
        player_name="Player 2",
        submitted_from="online",
        is_builtin=False,
    )

    async def get_player_mock(player_id: str):
        if player_id == "player-1":
            return player1
        elif player_id == "player-2":
            return player2
        return None

    db.get_player = AsyncMock(side_effect=get_player_mock)
    return db


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for testing."""
    session_mgr = AsyncMock()
    session_mgr.create_session = AsyncMock(return_value="session-123")
    return session_mgr


@pytest.fixture
def lobby_service(mock_db_service, mock_session_manager):
    """Create LobbyService instance with mocked dependencies."""
    service = LobbyService(session_manager=mock_session_manager, db_service=mock_db_service)
    return service


@pytest.mark.asyncio
async def test_join_queue_single_player_waits(lobby_service, mock_db_service):
    """Test that a single player joining the queue waits for a match."""
    request = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )

    # Start join_queue in background (it should block)
    task = asyncio.create_task(lobby_service.join_queue(request))

    # Give it time to process
    await asyncio.sleep(0.1)

    # Task should still be running (waiting for match)
    assert not task.done()

    # Verify queue size
    queue_size = await lobby_service.get_queue_size()
    assert queue_size == 1

    # Cancel the task to clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_join_queue_two_players_auto_match(lobby_service, mock_db_service, mock_session_manager):
    """Test that two players joining the queue are automatically matched."""
    request1 = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )
    request2 = LobbyJoinRequest(
        player_id="player-2",
        bot_config=PlayerConfig(player_id="player-2", bot_type="player"),
    )

    # Start both players joining concurrently
    task1 = asyncio.create_task(lobby_service.join_queue(request1))
    task2 = asyncio.create_task(lobby_service.join_queue(request2))

    # Wait for both to complete
    result1, result2 = await asyncio.gather(task1, task2)

    # Both should receive the same session_id
    assert result1.session_id == "session-123"
    assert result2.session_id == "session-123"

    # Verify opponent information
    assert result1.opponent_id == "player-2"
    assert result1.opponent_name == "Player 2"
    assert result2.opponent_id == "player-1"
    assert result2.opponent_name == "Player 1"

    # Verify session was created with correct config
    mock_session_manager.create_session.assert_called_once()
    call_args = mock_session_manager.create_session.call_args
    assert call_args.kwargs["visualize"] is True

    # Queue should be empty after matching
    queue_size = await lobby_service.get_queue_size()
    assert queue_size == 0


@pytest.mark.asyncio
async def test_join_queue_fifo_ordering(lobby_service, mock_db_service, mock_session_manager):
    """Test that players are matched in FIFO order."""
    # Create three players
    player3 = Player(
        player_id="player-3",
        player_name="Player 3",
        submitted_from="online",
        is_builtin=False,
    )

    async def get_player_mock(player_id: str):
        if player_id == "player-1":
            return Player(
                player_id="player-1",
                player_name="Player 1",
                submitted_from="online",
                is_builtin=False,
            )
        elif player_id == "player-2":
            return Player(
                player_id="player-2",
                player_name="Player 2",
                submitted_from="online",
                is_builtin=False,
            )
        elif player_id == "player-3":
            return player3
        return None

    mock_db_service.get_player = AsyncMock(side_effect=get_player_mock)

    # Player 1 joins first
    request1 = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )
    task1 = asyncio.create_task(lobby_service.join_queue(request1))

    # Give player 1 time to join
    await asyncio.sleep(0.05)

    # Player 2 joins second
    request2 = LobbyJoinRequest(
        player_id="player-2",
        bot_config=PlayerConfig(player_id="player-2", bot_type="player"),
    )
    task2 = asyncio.create_task(lobby_service.join_queue(request2))

    # Wait for first match to complete (player 1 and player 2)
    result1, result2 = await asyncio.gather(task1, task2)

    # Verify player 1 matched with player 2
    assert result1.opponent_id == "player-2"
    assert result2.opponent_id == "player-1"

    # Now player 3 joins
    request3 = LobbyJoinRequest(
        player_id="player-3",
        bot_config=PlayerConfig(player_id="player-3", bot_type="player"),
    )
    task3 = asyncio.create_task(lobby_service.join_queue(request3))

    # Give it time to process
    await asyncio.sleep(0.05)

    # Player 3 should still be waiting
    assert not task3.done()
    queue_size = await lobby_service.get_queue_size()
    assert queue_size == 1

    # Clean up
    task3.cancel()
    try:
        await task3
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_join_queue_player_not_found(lobby_service, mock_db_service):
    """Test that joining with non-existent player raises PlayerNotFoundError."""
    request = LobbyJoinRequest(
        player_id="nonexistent",
        bot_config=PlayerConfig(player_id="nonexistent", bot_type="player"),
    )

    with pytest.raises(PlayerNotFoundError) as exc_info:
        await lobby_service.join_queue(request)

    assert "nonexistent" in str(exc_info.value)


@pytest.mark.asyncio
async def test_join_queue_player_already_in_queue(lobby_service, mock_db_service):
    """Test that a player cannot join the queue twice."""
    request = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )

    # First join
    task1 = asyncio.create_task(lobby_service.join_queue(request))

    # Give it time to join queue
    await asyncio.sleep(0.05)

    # Second join attempt should fail
    with pytest.raises(PlayerAlreadyInLobbyError) as exc_info:
        await lobby_service.join_queue(request)

    assert "player-1" in str(exc_info.value)

    # Clean up
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_get_queue_size(lobby_service, mock_db_service):
    """Test get_queue_size returns correct count."""
    # Initially empty
    assert await lobby_service.get_queue_size() == 0

    # Add one player
    request1 = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )
    task1 = asyncio.create_task(lobby_service.join_queue(request1))
    await asyncio.sleep(0.05)

    assert await lobby_service.get_queue_size() == 1

    # Clean up
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_get_player_position(lobby_service, mock_db_service):
    """Test get_player_position returns correct position."""
    # Add two players
    request1 = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )
    task1 = asyncio.create_task(lobby_service.join_queue(request1))
    await asyncio.sleep(0.05)

    # Player 1 should be first
    position = await lobby_service.get_player_position("player-1")
    assert position == 1

    # Non-existent player
    position = await lobby_service.get_player_position("nonexistent")
    assert position is None

    # Clean up
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_remove_from_queue(lobby_service, mock_db_service):
    """Test removing a player from the queue."""
    request1 = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )
    task1 = asyncio.create_task(lobby_service.join_queue(request1))
    await asyncio.sleep(0.05)

    # Verify player is in queue
    assert await lobby_service.get_queue_size() == 1

    # Remove player
    removed = await lobby_service.remove_from_queue("player-1")
    assert removed is True

    # Queue should be empty
    assert await lobby_service.get_queue_size() == 0

    # Removing non-existent player
    removed = await lobby_service.remove_from_queue("nonexistent")
    assert removed is False

    # Clean up
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_service_initialization_errors(mock_db_service, mock_session_manager):
    """Test that LobbyService raises errors when dependencies not set."""
    service = LobbyService()

    request = LobbyJoinRequest(
        player_id="player-1",
        bot_config=PlayerConfig(player_id="player-1", bot_type="player"),
    )

    with pytest.raises(RuntimeError, match="SessionManager not set"):
        await service.join_queue(request)

    # Set session manager but not db service
    service.set_session_manager(mock_session_manager)

    with pytest.raises(RuntimeError, match="DatabaseService not set"):
        await service.join_queue(request)
