"""Tests to verify database isolation between tests and production."""

import os
import uuid
from pathlib import Path

import pytest


def test_override_test_database_fixture_sets_env_var(override_test_database):
    """Verify that override_test_database fixture sets PLAYGROUND_DATABASE_URL."""
    # Check that environment variable is set
    assert "PLAYGROUND_DATABASE_URL" in os.environ

    # Check that it points to test database, not production
    db_url = os.environ["PLAYGROUND_DATABASE_URL"]
    assert "test.db" in db_url
    assert "playground.db" not in db_url


def test_test_database_path_is_correct(override_test_database):
    """Verify that test database path is resolved correctly."""
    test_db_path = override_test_database

    # Verify it's an absolute path
    assert test_db_path.is_absolute()

    # Verify it's in the data/ directory
    assert test_db_path.parent.name == "data"

    # Verify filename is test.db
    assert test_db_path.name == "test.db"


def test_production_database_not_in_test_url(override_test_database):
    """Verify that test database URL does not point to production database."""
    db_url = os.environ.get("PLAYGROUND_DATABASE_URL", "")

    # Should NOT contain playground.db
    assert "playground.db" not in db_url

    # Should contain test.db
    assert "test.db" in db_url


@pytest.mark.asyncio
async def test_e2e_tests_use_test_database(asgi_client):
    """Verify that e2e tests actually use the test database.

    This test creates a player and verifies the operation completes successfully.
    The player data should be written to test.db, not playground.db.
    """
    # Use unique player name to avoid conflicts between test runs
    unique_name = f"DB Isolation Test {uuid.uuid4().hex[:8]}"

    # Register a test player
    payload = {
        "player_name": unique_name,
        "submitted_from": "online",
    }

    response = await asgi_client.post("/players/register", json=payload)
    assert response.status_code == 201  # 201 Created for new player registration

    player_data = response.json()
    assert player_data["player_name"] == unique_name

    # Verify we can retrieve the player (should be in test.db)
    player_id = player_data["player_id"]
    get_response = await asgi_client.get(f"/players/{player_id}")
    assert get_response.status_code == 200  # 200 OK for GET request


def test_production_database_exists_separately():
    """Verify that production database path is different from test database."""
    # Get repository root
    repo_root = Path(__file__).resolve().parents[2]

    # Production database should be at data/playground.db
    prod_db_path = repo_root / "data" / "playground.db"

    # Test database should be at data/test.db
    test_db_url = os.environ.get("PLAYGROUND_DATABASE_URL", "")

    # Verify test URL does not point to production path
    assert str(prod_db_path) not in test_db_url
