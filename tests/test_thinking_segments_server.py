# tests/test_thinking_segments_server.py
"""Server-level tests for thinking_segments in GET /messages."""
from pathlib import Path
from starlette.testclient import TestClient
from aede.db import DB
from aede.session import Session
from ulid import ULID


def _make_app(tmp_path: Path):
    """Minimal app wiring matching test_server_sessions.py pattern."""
    from aede.server import app
    from aede.config import load_config
    db = DB(tmp_path / "t.db")
    cfg = load_config(home=tmp_path, project_dir=tmp_path)
    app.state.db = db
    app.state.cfg = cfg
    return app, db


def test_get_messages_includes_thinking_segments(tmp_path):
    app, db = _make_app(tmp_path)
    s = Session.create(db, "claude-code", parent_id=None)
    mid = str(ULID())
    db.insert_message(id=mid, session_id=s.id, role="assistant", content="answer", token_count=5)
    db.insert_thinking_segment(message_id=mid, text="thought A", seq=0)
    db.insert_thinking_segment(message_id=mid, text="thought B", seq=2)

    with TestClient(app) as client:
        resp = client.get(f"/api/sessions/{s.id}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    asst = next(m for m in msgs if m["id"] == mid)
    assert "thinking_segments" in asst
    segs = asst["thinking_segments"]
    assert len(segs) == 2
    assert segs[0]["text"] == "thought A"
    assert segs[0]["seq"] == 0
    assert segs[1]["text"] == "thought B"
    assert segs[1]["seq"] == 2


def test_get_messages_empty_segments_for_native_provider(tmp_path):
    """Native provider messages have thinking col but no segments — segments list is empty."""
    app, db = _make_app(tmp_path)
    s = Session.create(db, "claude-3-5-sonnet", parent_id=None)
    mid = str(ULID())
    db.insert_message(id=mid, session_id=s.id, role="assistant", content="answer", token_count=5)
    db.update_message(id=mid, content="answer", token_count=5, thinking="big blob")

    with TestClient(app) as client:
        resp = client.get(f"/api/sessions/{s.id}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    asst = next(m for m in msgs if m["id"] == mid)
    # thinking col preserved, segments list empty
    assert asst.get("thinking") == "big blob"
    assert asst.get("thinking_segments") == []
