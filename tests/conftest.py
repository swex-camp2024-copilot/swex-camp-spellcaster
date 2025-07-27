"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add the project root to sys.path for all tests
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture
def sample_game_state():
    """Provide a sample game state for testing bot logic."""
    return {
        "my_wizard": {
            "position": [5, 5],
            "health": 100,
            "mana": 50,
            "spells": ["fireball", "heal", "shield"]
        },
        "enemy_wizards": [
            {
                "position": [3, 3],
                "health": 80,
                "mana": 30
            }
        ],
        "minions": [],
        "artifacts": [],
        "board_size": [10, 10],
        "turn": 1
    }


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    from unittest.mock import MagicMock
    from bots.bot_interface import BotInterface
    
    bot = MagicMock(spec=BotInterface)
    bot.name = "TestBot"
    bot.decide.return_value = {
        "move": [0, 1],
        "spell": None
    }
    return bot 