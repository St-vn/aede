import asyncio
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
    return TestClient(app)


class _StallAgent:
    """AgentLoop that blocks on an asyncio.Event during run_turn."""

    _started = asyncio.Event()

    def __init__(self, *args, **kwargs):
        self._gate_backend = kwargs.get("gate_backend")
        self._current_assist_id = None

    def initialize(self, *args, **kwargs):
        pass

    async def run_turn(self, user_input):
        _StallAgent._started.set()
        await asyncio.Event().wait()


def test_stop_message_cancels_turn(client, db):
    _StallAgent._started.clear()
    s = Session.create(db, "sonnet-4", parent_id=None)
    with patch("aede.agent.AgentLoop", _StallAgent):
        with client.websocket_connect(f"/ws/sessions/{s.id}") as ws:
            ws.send_json({"type": "user_message", "content": "go"})
            import time
            # Wait for the stall agent to actually start running
            for _ in range(50):
                if _StallAgent._started.is_set():
                    break
                time.sleep(0.01)
            ws.send_json({"type": "stop"})
            ev = ws.receive_json()
            assert ev["type"] == "turn_completed"


def test_stop_message_no_active_turn(client, db):
    """Sending stop when no turn is active should not error."""
    s = Session.create(db, "sonnet-4", parent_id=None)
    with client.websocket_connect(f"/ws/sessions/{s.id}") as ws:
        ws.send_json({"type": "stop"})
        import time
        time.sleep(0.2)
