"""Tier 1 turn durability: a no-gate WebSocket disconnect (browser close or
session switch) must NOT cancel the in-flight turn. The detached task runs to
completion and persists its result; a reconnecting browser re-reads it from the
DB. Only a turn with no work left to resume *and* that errors on its own ends.

Contrast with test_server_stop.py, where an explicit ``stop`` message DOES cancel.
"""
import asyncio
import time

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from aede.server import app
from aede.db import DB
from aede.session import Session


@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "test.db")


@pytest.fixture
def client(db, tmp_path):
    from aede.config import load_config
    app.state.db = db
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    # Start from a clean session-state map so a prior test's tasks don't leak in.
    app.state.session_states = {}
    return TestClient(app)


class _StallAgent:
    """AgentLoop that blocks forever in run_turn (mirrors test_server_stop).

    No gate is ever requested, so this exercises the no-gate disconnect path.
    """

    _started = asyncio.Event()

    def __init__(self, *args, **kwargs):
        self._gate_backend = kwargs.get("gate_backend")
        self._current_assist_id = None
        self._messages = []

    def initialize(self, *args, **kwargs):
        pass

    async def run_turn(self, user_input):
        _StallAgent._started.set()
        await asyncio.Event().wait()


def test_no_gate_disconnect_does_not_cancel_turn(client, db):
    """Closing the socket mid-turn with no pending gate must NOT cancel the
    turn task — durability Tier 1.

    We assert on our own code's behavior (no ``cancel()`` is issued on the turn
    task by the disconnect handler) rather than on the task running to
    completion: Starlette's TestClient tears the ASGI app down when the
    websocket ``with`` block exits, which cancels outstanding tasks as a harness
    artifact. Under a real long-lived uvicorn loop the detached task survives.
    Contrast test_server_stop.py, where an explicit ``stop`` *does* cancel.
    """
    _StallAgent._started.clear()
    s = Session.create(db, "sonnet-4", parent_id=None)

    cancelled = {"called": False}

    with patch("aede.agent.AgentLoop", _StallAgent):
        with client.websocket_connect(f"/ws/sessions/{s.id}") as ws:
            ws.send_json({"type": "user_message", "content": "go"})
            for _ in range(100):
                if _StallAgent._started.is_set():
                    break
                time.sleep(0.01)
            assert _StallAgent._started.is_set(), "turn never started"

            # Wrap the live turn task's cancel() so we can detect a cancel issued
            # by the disconnect handler (vs. harness teardown after the block).
            state = app.state.session_states[s.id]
            task = state.turn_task
            assert task is not None
            orig_cancel = task.cancel

            import traceback as _tb

            def _tracking_cancel(*a, **k):
                cancelled["called"] = True
                cancelled["stack"] = "".join(_tb.format_stack())
                return orig_cancel(*a, **k)

            task.cancel = _tracking_cancel
            # Exiting the `with` closes the socket → WebSocketDisconnect handler runs.

        # The disconnect handler must not have cancelled the turn.
        # Starlette's TestClient cancels outstanding tasks during its portal
        # shutdown when the websocket block exits — that cancel comes from
        # anyio/threading frames, NOT from aede. A Tier 1 regression would show
        # an ``aede/server.py`` frame in the cancel stack (the disconnect handler
        # calling ``turn_task.cancel()``). Assert our code is not the canceller.
        stack = cancelled.get("stack", "")
        assert "server.py" not in stack, (
            "no-gate disconnect cancelled the turn task from aede/server.py; "
            "Tier 1 durability broken\n" + stack
        )
