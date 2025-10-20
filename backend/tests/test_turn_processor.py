import pytest
import asyncio

from backend.app.services.turn_processor import TurnProcessor
from backend.app.models.actions import ActionData


@pytest.mark.asyncio
async def test_collect_actions_all_present():
    tp = TurnProcessor(timeout_seconds=0.1)
    session_id = "s1"
    turn = 1
    players = ["p1", "p2"]

    await tp.submit_action(session_id, "p1", turn, ActionData(move=[1, 0], spell=None))
    await tp.submit_action(session_id, "p2", turn, ActionData(move=[0, 1], spell=None))

    collected = await tp.collect_actions(session_id, turn, players)
    assert set(collected.keys()) == set(players)
    assert collected["p1"].move == [1, 0]
    assert collected["p2"].move == [0, 1]


@pytest.mark.asyncio
async def test_collect_actions_timeout_fills_defaults():
    tp = TurnProcessor(timeout_seconds=0.05)
    session_id = "s2"
    turn = 2
    players = ["p1", "p2"]

    await tp.submit_action(session_id, "p1", turn, ActionData(move=None, spell=None))
    collected = await tp.collect_actions(session_id, turn, players)

    assert set(collected.keys()) == set(players)
    assert collected["p1"].move is None
    assert collected["p2"].move == [0, 0]


@pytest.mark.asyncio
async def test_collect_actions_autofill_builtin():
    tp = TurnProcessor(timeout_seconds=0.05)
    session_id = "s3"
    turn = 3
    players = ["p1", "p2"]

    def is_builtin(pid: str) -> bool:
        return pid == "p1"

    collected = await tp.collect_actions(session_id, turn, players, is_builtin=is_builtin)
    assert collected["p1"].move is None  # builtin auto placeholder
    assert collected["p2"].move == [0, 0]  # timeout default
