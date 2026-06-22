import pytest
from aede.db import DB
from aede.session import Session


from ulid import ULID


def _msg_id():
    return str(ULID())


def test_rewind_creates_branch(tmp_path):
    db = DB(tmp_path / "test.db")
    s = Session.create(db, "sonnet-4", parent_id=None)
    mid = _msg_id()
    db.insert_message(id=mid, session_id=s.id, role="user", content="hello", token_count=None)
    s2 = Session.fork_from_message(db, s.id, mid)
    assert s2.parent_id == s.id
    assert s2.branch_message_id == mid


def test_rewind_fork_round_trip(tmp_path):
    db = DB(tmp_path / "test.db")
    s = Session.create(db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    db.insert_message(id=m2, session_id=s.id, role="user", content="second", token_count=None)
    s2 = Session.fork_from_message(db, s.id, m1)
    assert s2.parent_id == s.id
    assert s2.branch_message_id == m1
    loaded = Session.load(db, s2.id)
    assert loaded.branch_message_id == m1
    assert loaded.parent_id == s.id


def test_rewind_endpoint_returns_new_session(tmp_path):
    from aede.server import app
    from aede.config import load_config
    from fastapi.testclient import TestClient
    app.state.db = DB(tmp_path / "test.db")
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    client = TestClient(app)
    s = Session.create(app.state.db, "sonnet-4", parent_id=None)
    mid = _msg_id()
    app.state.db.insert_message(id=mid, session_id=s.id, role="user", content="hello", token_count=None)
    resp = client.post(f"/api/sessions/{s.id}/rewind", json={"message_id": mid})
    assert resp.status_code == 200
    data = resp.json()
    assert data["parent_id"] == s.id
    assert data["branch_message_id"] == mid
