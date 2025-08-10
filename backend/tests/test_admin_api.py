import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import create_tables


@pytest.mark.asyncio
async def test_admin_endpoints_exist_and_return_json():
    await create_tables()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=5.0) as ac:
        # Players list
        resp = await ac.get("/admin/players")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # Start a session to populate active list
        payload = {
            "player_1_config": {"player_id": "builtin_sample_1", "bot_type": "builtin", "bot_id": "sample_bot_1"},
            "player_2_config": {"player_id": "builtin_sample_2", "bot_type": "builtin", "bot_id": "sample_bot_2"},
        }
        start = await ac.post("/playground/start", json=payload)
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        # Give the loop a short time
        await asyncio.sleep(0.1)

        resp = await ac.get("/playground/active")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # Cleanup session via admin
        del_resp = await ac.delete(f"/playground/{session_id}")
        assert del_resp.status_code == 200
        assert del_resp.json().get("status") == "terminated"

