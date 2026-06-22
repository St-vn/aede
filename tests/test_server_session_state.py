import asyncio
import pytest
from aede.server import SessionState


def test_session_state_tracks_turn_task():
    state = SessionState()
    assert state.turn_task is None
    assert state.gate is not None


def test_session_state_stores_turn_id():
    state = SessionState()
    assert state.current_turn_id is None
    state.current_turn_id = "turn_001"
    assert state.current_turn_id == "turn_001"


@pytest.mark.asyncio
async def test_session_state_can_store_task():
    state = SessionState()
    task = asyncio.create_task(asyncio.sleep(0))
    state.turn_task = task
    assert state.turn_task is task
    await task
