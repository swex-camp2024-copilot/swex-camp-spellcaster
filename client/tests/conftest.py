"""Test configuration and fixtures for client tests."""

import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport, Timeout

# IMPORTANT: Set test database URL BEFORE importing backend.app.main
# The database engine is created at import time, so we must override the env var first
_repo_root = Path(__file__).resolve().parents[2]
_test_db_path = _repo_root / "data" / "test.db"
_test_db_url = f"sqlite+aiosqlite:///{_test_db_path.as_posix()}"
os.environ["PLAYGROUND_DATABASE_URL"] = _test_db_url

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def override_test_database():
    """Override database URL for e2e tests to use separate test database.

    This fixture runs automatically before any tests and ensures e2e tests
    use data/test.db instead of the production data/playground.db.

    Note: The environment variable is set at module import time (above) to ensure
    it's set before the backend.app.main module creates the database engine.
    """
    yield _test_db_path

    # Cleanup: Remove test database after all tests complete
    if _test_db_path.exists():
        _test_db_path.unlink()
        print(f"\n✓ Cleaned up test database: {_test_db_path}")


@pytest_asyncio.fixture
async def asgi_client(override_test_database):
    """Create test client with proper app lifecycle.

    This fixture properly starts and stops the FastAPI app with all its services,
    including the StateManager initialization.

    Depends on override_test_database to ensure test database is used.
    """
    # Manually trigger lifespan events to initialize StateManager
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=Timeout(10.0)) as client:
            yield client
