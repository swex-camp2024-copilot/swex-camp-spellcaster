"""Test configuration and fixtures for the Spellcasters Playground Backend."""

import asyncio
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from backend.app.core.config import Settings
from backend.app.models.database import PlayerDB, SessionDB
from backend.app.models.players import Player, PlayerRegistration
from backend.app.models.sessions import GameState, PlayerSlot

# Test database settings
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings with in-memory database."""
    return Settings(
        database_url=TEST_DATABASE_URL, database_echo=False, turn_timeout_seconds=1.0, match_loop_delay_seconds=0.1
    )


@pytest.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session


@pytest.fixture
def sample_player_registration():
    """Create a sample player registration."""
    return PlayerRegistration(player_name="TestPlayer", submitted_from="pasted", sprite_path="assets/wizards/test.png")


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(
        player_id=str(uuid4()), player_name="TestPlayer", submitted_from="pasted", sprite_path="assets/wizards/test.png"
    )


@pytest.fixture
def sample_builtin_player():
    """Create a sample built-in player."""
    return Player(
        player_id="builtin_sample_1",
        player_name="Sample Bot 1",
        submitted_from="builtin",
        sprite_path="assets/wizards/sample_bot1.png",
        is_builtin=True,
    )


@pytest.fixture
def sample_player_slot():
    """Create a sample player slot."""
    return PlayerSlot(
        player_id=str(uuid4()), player_name="TestPlayer", is_builtin_bot=False, hp=100, mana=50, position=[4, 4]
    )


@pytest.fixture
def sample_game_state(sample_player_slot):
    """Create a sample game state."""
    slot2 = PlayerSlot(
        player_id=str(uuid4()), player_name="TestPlayer2", is_builtin_bot=True, hp=100, mana=50, position=[2, 2]
    )

    return GameState(session_id=str(uuid4()), player_1=sample_player_slot, player_2=slot2)


@pytest.fixture
async def sample_player_db(test_session):
    """Create and persist a sample player in the database."""
    player = PlayerDB(
        player_id=str(uuid4()),
        player_name="TestPlayer",
        submitted_from="pasted",
        total_matches=0,
        wins=0,
        losses=0,
        draws=0,
    )

    test_session.add(player)
    await test_session.commit()
    await test_session.refresh(player)

    return player


@pytest.fixture
async def sample_session_db(test_session, sample_player_db):
    """Create and persist a sample session in the database."""
    # Create second player
    player2 = PlayerDB(player_id=str(uuid4()), player_name="TestPlayer2", submitted_from="builtin", is_builtin=True)
    test_session.add(player2)
    await test_session.commit()

    # Create session
    session = SessionDB(
        session_id=str(uuid4()),
        player_1_id=sample_player_db.player_id,
        player_2_id=player2.player_id,
        status="active",
        turn_index=0,
    )

    test_session.add(session)
    await test_session.commit()
    await test_session.refresh(session)

    return session


@pytest.fixture
def mock_game_engine_state():
    """Mock game engine state for testing."""
    return {
        "board": {"width": 8, "height": 8, "artifacts": []},
        "players": {
            "player1": {"hp": 100, "mana": 50, "position": [4, 4], "spells": ["fireball", "heal", "shield"]},
            "player2": {"hp": 100, "mana": 50, "position": [2, 2], "spells": ["fireball", "heal", "shield"]},
        },
        "turn": 1,
        "status": "active",
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "database: marks tests that require database")


# Custom pytest markers for test organization
pytestmark = [
    pytest.mark.asyncio,  # All tests in this module are async
]
