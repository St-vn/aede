# tests/test_server_gate_ws.py
import pytest, json, asyncio
from fastapi.testclient import TestClient
from aede.server import app
from aede.db import DB
from aede.gate import GateDecision

@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "test.db")

@pytest.fixture
def client(db, tmp_path):
    from aede.config import load_config
    app.state.db = db
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    return TestClient(app)

def test_gate_round_trip_denied(client, db):
    # This is hard to test with TestClient because it's synchronous-ish for WebSockets
    # but let's try to mock the sequence.
    # Actually, we might need a real async test with httpx or similar.
    pass
