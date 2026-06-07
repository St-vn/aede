# tests/test_server_sessions.py
import pytest
from fastapi.testclient import TestClient
from aede.server import app
from aede.db import DB
from aede.session import Session
from pathlib import Path

@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "test.db")

@pytest.fixture
def client(db, tmp_path):
    from aede.config import load_config
    app.state.db = db
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    return TestClient(app)

def test_get_sessions_empty(client):
    response = client.get("/sessions")
    assert response.status_code == 200
    assert response.json() == []

def test_get_sessions_with_data(client, db):
    s1 = Session.create(db, "model1", parent_id=None, title="Title 1")
    s2 = Session.create(db, "model2", parent_id=None)
    
    response = client.get("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(s["id"] == s1.id and s["title"] == "Title 1" for s in data)

def test_get_session_by_id(client, db):
    s1 = Session.create(db, "model1", parent_id=None)
    response = client.get(f"/sessions/{s1.id}")
    assert response.status_code == 200
    assert response.json()["id"] == s1.id

def test_get_session_not_found(client):
    response = client.get("/sessions/NONEXISTENT")
    assert response.status_code == 404

def test_get_messages(client, db):
    s1 = Session.create(db, "model1", parent_id=None)
    db.insert_message(id="m1", session_id=s1.id, role="user", content="hello", token_count=10)
    
    response = client.get(f"/sessions/{s1.id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "hello"

def test_patch_session_title(client, db):
    s1 = Session.create(db, "model1", parent_id=None, title="Old Title")
    response = client.patch(f"/sessions/{s1.id}", json={"title": "New Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    
    # Verify DB state updated
    loaded = Session.load(db, s1.id)
    assert loaded.title == "New Title"

