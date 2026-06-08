# tests/test_server_websocket.py
import pytest, json
from fastapi.testclient import TestClient
from aede.server import app
from aede.db import DB
from aede.session import Session
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

def test_websocket_connection(client, db):
    s1 = Session.create(db, "sonnet-4", parent_id=None)
    with client.websocket_connect(f"/ws/sessions/{s1.id}") as websocket:
        pass

@pytest.mark.asyncio
async def test_websocket_turn_streaming(db, tmp_path):
    client = TestClient(app)
    app.state.db = db
    from aede.config import load_config
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    s1 = Session.create(db, "sonnet-4", parent_id=None)
    
    with client.websocket_connect(f"/ws/sessions/{s1.id}") as ws:
        pass
