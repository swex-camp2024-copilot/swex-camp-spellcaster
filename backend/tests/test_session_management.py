"""Tests for session management and game flow."""

import pytest
from datetime import datetime
from unittest.mock import patch

from backend.app.models.players import PlayerConfig
from backend.app.services.session_manager import SessionManager


class DummyBot:
    def __init__(self, name, player_id):
        self._name = name
        self._player_id = player_id
        self._is_builtin = True

    @property
    def name(self):
        return self._name

    @property
    def player_id(self):
        return self._player_id

    @property
    def is_builtin(self):
        return self._is_builtin

    def decide(self, state):
        return {"move": [0, 0], "spell": None}


class DummyEngine:
    def __init__(self, bot1, bot2):
        self.bot1 = bot1
        self.bot2 = bot2
        self.turn = 0

        # Minimal API used by adapter
        class Wiz:
            def __init__(self, name):
                self.name = name
                self.hp = 100
                self.mana = 100
                self.position = [0, 0]

        self.wizard1 = Wiz(bot1.name)
        self.wizard2 = Wiz(bot2.name)

        class Logger:
            def __init__(self):
                self.current_turn = []

        self.logger = Logger()

    def build_input(self, w1, w2):
        return {
            "self": {"hp": 100, "mana": 100, "position": [0, 0]},
            "opponent": {"hp": 100, "mana": 100, "position": [0, 0]},
            "turn": self.turn,
            "artifacts": [],
            "minions": [],
        }

    def run_turn(self):
        self.turn += 1
        # Finish game after 2 turns
        if self.turn >= 2:
            self.wizard2.hp = 0

    def check_winner(self):
        if self.wizard1.hp <= 0 and self.wizard2.hp <= 0:
            return "Draw"
        if self.wizard2.hp <= 0:
            return self.bot1
        return None


@pytest.mark.asyncio
async def test_create_session_and_run_loop(monkeypatch):
    # Patch GameEngine symbol exposed by adapter
    from backend.app.services import game_adapter as ga

    ga.GameEngine = DummyEngine

    # Ensure DB tables exist for the async engine used by DatabaseService
    from backend.app.core.database import create_tables

    await create_tables()

    manager = SessionManager()

    # Use builtin configs (registry will build wrappers)
    p1 = PlayerConfig(player_id="builtin_sample_1", bot_type="builtin", bot_id="sample_bot_1")
    p2 = PlayerConfig(player_id="builtin_sample_2", bot_type="builtin", bot_id="sample_bot_2")

    session_id = await manager.create_session(p1, p2)

    # Wait a small amount for loop to complete
    # In real tests we'd add synchronization; for now sleep briefly
    import asyncio

    await asyncio.sleep(0.2)

    ctx = await manager.get_session(session_id)
    assert ctx.game_state.turn_index >= 1
    # Cleanup
    await manager.cleanup_session(session_id)
