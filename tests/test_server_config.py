# tests/test_server_config.py
import pytest
from fastapi.testclient import TestClient
from aede.server import app
from aede.db import DB
from aede.tokens import TokenTracker

@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "test.db")

@pytest.fixture
def client(db, tmp_path):
    from aede.config import load_config
    app.state.db = db
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    return TestClient(app)

def test_get_config(client):
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "shell" in data


def test_get_api_config(client):
    """GET /api/config must serialize cleanly (regression: #63 removed the
    SandboxConfig dataclass but the endpoint still called dataclasses.asdict
    on the now-missing cfg.sandbox → 500)."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    # sandbox is rebuilt from the flat cfg.sandbox_* fields, not the deleted dataclass.
    assert "sandbox" in data
    assert "enabled" in data["sandbox"]
    assert "image" in data["sandbox"]


def test_get_token_usage_empty(client):
    response = client.get("/token_usage")
    assert response.status_code == 200
    assert response.json() == {"total_input_tokens": 0, "total_output_tokens": 0, "total_cached_tokens": 0}

def test_get_token_usage_with_data(client, db):
    from aede.session import Session
    s1 = Session.create(db, "model1", parent_id=None)
    tracker = TokenTracker(session_id=s1.id, db=db)
    tracker.record(turn=1, input_tokens=100, output_tokens=50, cached_tokens=10)
    
    response = client.get("/token_usage")
    assert response.status_code == 200
    data = response.json()
    assert data["total_input_tokens"] == 100
    assert data["total_output_tokens"] == 50
    assert data["total_cached_tokens"] == 10
