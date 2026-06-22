"""
Tests for the POST /api/sessions/{id}/truncate endpoint and supporting DB/Session helpers.

The truncate endpoint deletes all messages in the current session whose
``created_at`` is strictly greater than the timestamp of the supplied
``message_id``, optionally running the three-tier code-revert utility against
the tool_calls of those messages.  It returns the SAME session dict (not a
new one) so the client can stay on the same session ID.
"""
from pathlib import Path

import pytest
from ulid import ULID

from aede.db import DB
from aede.session import Session


def _msg_id() -> str:
    return str(ULID())


def test_db_delete_messages_after_removes_only_strictly_newer(tmp_path: Path):
    db = DB(tmp_path / "test.db")
    s = Session.create(db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    m3 = _msg_id()
    db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    import time
    time.sleep(0.005)
    db.insert_message(id=m2, session_id=s.id, role="assistant", content="reply", token_count=None)
    time.sleep(0.005)
    db.insert_message(id=m3, session_id=s.id, role="user", content="third", token_count=None)

    rows = db.get_messages(s.id)
    assert len(rows) == 3
    target_ts = next(r["created_at"] for r in rows if r["id"] == m2)

    db.delete_messages_after(s.id, target_ts)

    remaining = db.get_messages(s.id)
    assert [r["id"] for r in remaining] == [m1, m2]


def test_db_delete_messages_after_cascades_tool_calls(tmp_path: Path):
    db = DB(tmp_path / "test.db")
    s = Session.create(db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    import time
    time.sleep(0.005)
    db.insert_message(id=m2, session_id=s.id, role="assistant", content="second", token_count=None)
    db.insert_tool_call(id=str(ULID()), message_id=m2, tool_name="write_file", args="{}", status="ok", provider='aede')

    rows = db.get_messages(s.id)
    target_ts = next(r["created_at"] for r in rows if r["id"] == m1)

    db.delete_messages_after(s.id, target_ts)

    remaining_msgs = db.get_messages(s.id)
    assert [r["id"] for r in remaining_msgs] == [m1]
    tc_map = db.get_tool_calls_for_message_ids([m1, m2])
    assert tc_map == {}


def test_db_delete_messages_after_with_boundary_id_handles_same_ms(tmp_path: Path):
    """When two messages share the same created_at, boundary_id is used as
    a tie-breaker so the boundary message is preserved and the next one
    is removed — the realistic case for in-place rewind."""
    db = DB(tmp_path / "test.db")
    s = Session.create(db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    db.insert_message(id=m1, session_id=s.id, role="user", content="boundary", token_count=None)
    db.insert_message(id=m2, session_id=s.id, role="assistant", content="after", token_count=None)

    fixed_ts = 1_700_000_000_000
    db.con.execute(
        "UPDATE messages SET created_at = ? WHERE session_id = ?",
        (fixed_ts, s.id),
    )
    db.con.commit()

    target_ts = next(
        r["created_at"] for r in db.get_messages(s.id) if r["id"] == m1
    )
    assert target_ts == next(
        r["created_at"] for r in db.get_messages(s.id) if r["id"] == m2
    )

    removed = db.delete_messages_after(s.id, target_ts, boundary_id=m1)
    assert removed == 1
    remaining = db.get_messages(s.id)
    assert [r["id"] for r in remaining] == [m1]


def test_truncate_session_classmethod_returns_same_session(tmp_path: Path):
    db = DB(tmp_path / "test.db")
    s = Session.create(db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    db.insert_message(id=m2, session_id=s.id, role="assistant", content="reply", token_count=None)

    result = Session.truncate_after_message(db, s.id, m1)
    assert result.id == s.id
    assert [r["id"] for r in db.get_messages(s.id)] == []


def test_truncate_endpoint_removes_target_and_messages_after_message_id(tmp_path: Path):
    from fastapi.testclient import TestClient

    from aede.config import load_config
    from aede.server import app

    app.state.db = DB(tmp_path / "test.db")
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    client = TestClient(app)

    s = Session.create(app.state.db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    m3 = _msg_id()
    app.state.db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    app.state.db.insert_message(id=m2, session_id=s.id, role="assistant", content="reply", token_count=None)
    app.state.db.insert_message(id=m3, session_id=s.id, role="user", content="third", token_count=None)

    resp = client.post(
        f"/api/sessions/{s.id}/truncate",
        json={"message_id": m1, "revert_code": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == s.id
    remaining_ids = [m["id"] for m in app.state.db.get_messages(s.id)]
    assert remaining_ids == []


def test_truncate_endpoint_returns_same_session_id(tmp_path: Path):
    from fastapi.testclient import TestClient

    from aede.config import load_config
    from aede.server import app

    app.state.db = DB(tmp_path / "test.db")
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    client = TestClient(app)

    s = Session.create(app.state.db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    app.state.db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)

    resp = client.post(
        f"/api/sessions/{s.id}/truncate",
        json={"message_id": m1, "revert_code": False},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == s.id
    assert [m["id"] for m in app.state.db.get_messages(s.id)] == []


def test_truncate_endpoint_with_revert_code_invokes_revert_utility(tmp_path: Path, monkeypatch):
    from fastapi.testclient import TestClient

    from aede.config import load_config
    from aede.server import app

    app.state.db = DB(tmp_path / "test.db")
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    client = TestClient(app)

    s = Session.create(app.state.db, "sonnet-4", parent_id=None, project_dir=str(tmp_path))
    m1 = _msg_id()
    m2 = _msg_id()
    app.state.db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    app.state.db.insert_message(id=m2, session_id=s.id, role="assistant", content="reply", token_count=None)
    app.state.db.insert_tool_call(
        id=str(ULID()),
        message_id=m2,
        tool_name="write_file",
        args='{}',
        status="ok",
        provider='aede',
    )

    called: list[tuple[Path, list[dict]]] = []

    def fake_revert(project_dir, tool_calls):
        called.append((project_dir, tool_calls))
        return []

    from aede.tools import rewind as rewind_mod

    monkeypatch.setattr(rewind_mod, "revert_code", fake_revert)
    monkeypatch.setattr("aede.server.revert_code", fake_revert, raising=False)

    resp = client.post(
        f"/api/sessions/{s.id}/truncate",
        json={"message_id": m1, "revert_code": True},
    )
    assert resp.status_code == 200
    assert called, "revert_code should be invoked when revert_code=True"
    project_dir_arg, tcs_arg = called[0]
    assert isinstance(project_dir_arg, Path)
    assert any(tc.get("name") == "write_file" for tc in tcs_arg)
    assert [m["id"] for m in app.state.db.get_messages(s.id)] == []


def test_truncate_endpoint_cascades_thinking_segments(tmp_path: Path):
    from fastapi.testclient import TestClient

    from aede.config import load_config
    from aede.server import app

    app.state.db = DB(tmp_path / "test.db")
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    client = TestClient(app)

    s = Session.create(app.state.db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    app.state.db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    app.state.db.insert_message(id=m2, session_id=s.id, role="assistant", content="reply", token_count=None)
    app.state.db.insert_thinking_segment(
        message_id=m2, text="thinking...", seq=1
    )

    resp = client.post(
        f"/api/sessions/{s.id}/truncate",
        json={"message_id": m1, "revert_code": False},
    )
    assert resp.status_code == 200
    assert [m["id"] for m in app.state.db.get_messages(s.id)] == []
    seg_row = app.state.db.con.execute(
        "SELECT COUNT(*) AS cnt FROM thinking_segments WHERE message_id = ?", (m2,)
    ).fetchone()
    assert seg_row["cnt"] == 0


def test_truncate_endpoint_with_revert_code_false_does_not_revert(tmp_path: Path, monkeypatch):
    from fastapi.testclient import TestClient

    from aede.config import load_config
    from aede.server import app

    app.state.db = DB(tmp_path / "test.db")
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    client = TestClient(app)

    s = Session.create(app.state.db, "sonnet-4", parent_id=None)
    m1 = _msg_id()
    m2 = _msg_id()
    app.state.db.insert_message(id=m1, session_id=s.id, role="user", content="first", token_count=None)
    app.state.db.insert_message(id=m2, session_id=s.id, role="assistant", content="reply", token_count=None)

    called: list[tuple[Path, list[dict]]] = []

    def fake_revert(project_dir, tool_calls):
        called.append((project_dir, tool_calls))
        return []

    monkeypatch.setattr("aede.tools.rewind.revert_code", fake_revert)
    monkeypatch.setattr("aede.server.revert_code", fake_revert, raising=False)

    resp = client.post(
        f"/api/sessions/{s.id}/truncate",
        json={"message_id": m1, "revert_code": False},
    )
    assert resp.status_code == 200
    assert called == []
    assert [m["id"] for m in app.state.db.get_messages(s.id)] == []
