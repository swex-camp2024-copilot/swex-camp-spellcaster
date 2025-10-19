"""Test configuration and fixtures for client tests."""

import pytest_asyncio
from httpx import AsyncClient, ASGITransport, Timeout

from backend.app.main import app


@pytest_asyncio.fixture
async def asgi_client():
    """Create test client with proper app lifecycle.

    This fixture properly starts and stops the FastAPI app with all its services,
    including the StateManager initialization.
    """
    # Manually trigger lifespan events to initialize StateManager
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=Timeout(10.0)) as client:
            yield client
