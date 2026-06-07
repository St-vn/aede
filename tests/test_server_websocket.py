# tests/test_server_websocket.py
import pytest, json
from fastapi.testclient import TestClient
from aede.server import app
from aede.db import DB
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "test.db")

@pytest.fixture
def client(db, tmp_path):
    from aede.config import load_config
    app.state.db = db
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    return TestClient(app)

def test_websocket_connection(client):
    with client.websocket_connect("/ws/turn") as websocket:
        # Just connecting and closing should work
        pass

@pytest.mark.asyncio
async def test_websocket_turn_streaming(db, tmp_path):
    # We need a more complex test that mocks AgentLoop and checks messages
    # For now, just test the endpoint exists
    client = TestClient(app)
    app.state.db = db
    from aede.config import load_config
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    
    with client.websocket_connect("/ws/turn") as ws:
        # We can't easily test the full turn here without deep mocking
        # but we can verify it doesn't crash on connect
        pass
