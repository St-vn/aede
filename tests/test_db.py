import pytest
from pathlib import Path
from aede.db import DB


def test_db_creates_schema(tmp_home):
    db = DB(tmp_home / "data" / "aede.db")
    tables = db.con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {r["name"] for r in tables}
    assert "sessions" in names
    assert "messages" in names
    assert "tool_calls" in names
    assert "token_usage" in names


def test_db_wal_mode(tmp_home):
    db = DB(tmp_home / "data" / "aede.db")
    mode = db.con.execute("PRAGMA journal_mode").fetchone()["journal_mode"]
    assert mode == "wal"


def test_db_insert_and_get_session(tmp_home):
    db = DB(tmp_home / "data" / "aede.db")
    db.insert_session(
        id="01J000000000000000000000AA",
        parent_id=None,
        title="test session",
        model="claude-sonnet-4-20250514",
    )
    row = db.get_session("01J000000000000000000000AA")
    assert row["title"] == "test session"
    assert row["status"] == "active"
    assert row["parent_id"] is None


def test_db_insert_message(tmp_home):
    db = DB(tmp_home / "data" / "aede.db")
    db.insert_session(
        id="01J000000000000000000000AB",
        parent_id=None,
        title="msg test",
        model="claude-sonnet-4-20250514",
    )
    db.insert_message(
        id="01J000000000000000000000AC",
        session_id="01J000000000000000000000AB",
        role="user",
        content="hello",
        token_count=None,
    )
    msgs = db.get_messages("01J000000000000000000000AB")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "hello"


def test_db_update_session_status(tmp_home):
    db = DB(tmp_home / "data" / "aede.db")
    db.insert_session(
        id="01J000000000000000000000AD",
        parent_id=None,
        title="status test",
        model="claude-sonnet-4-20250514",
    )
    db.update_session_status("01J000000000000000000000AD", "archived")
    row = db.get_session("01J000000000000000000000AD")
    assert row["status"] == "archived"


def test_db_insert_token_usage(tmp_home):
    db = DB(tmp_home / "data" / "aede.db")
    db.insert_session(
        id="01J000000000000000000000AE",
        parent_id=None,
        title="token test",
        model="claude-sonnet-4-20250514",
    )
    db.insert_token_usage(
        id="01J000000000000000000000AF",
        session_id="01J000000000000000000000AE",
        turn_number=1,
        input_tokens=100,
        output_tokens=20,
        cached_tokens=80,
    )
    totals = db.get_token_totals("01J000000000000000000000AE")
    assert totals["input_tokens"] == 100
    assert totals["cached_tokens"] == 80


def test_db_list_sessions(tmp_home):
    db = DB(tmp_home / "data" / "aede.db")
    for i in range(3):
        db.insert_session(
            id=f"01J000000000000000000000A{i}",
            parent_id=None,
            title=f"session {i}",
            model="claude-sonnet-4-20250514",
        )
    rows = db.list_sessions(limit=10)
    assert len(rows) == 3


def test_resume_branch_messages(tmp_home):
    """Branch session gets correct parent_id; parent remains independently loadable;
    db.get_messages returns seeded rows for the parent."""
    from aede.session import Session

    db = DB(tmp_home / "aede.db")

    # Create parent session and seed two messages
    parent = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    db.insert_message(
        id="01J000000000000000000000M1",
        session_id=parent.id,
        role="user",
        content="Hello parent",
        token_count=None,
    )
    db.insert_message(
        id="01J000000000000000000000M2",
        session_id=parent.id,
        role="assistant",
        content="Hi from assistant",
        token_count=10,
    )

    # Create a branch (child) session pointing at the parent
    branch = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=parent.id)

    # Branch must carry the parent reference
    assert branch.parent_id == parent.id

    # Parent is still independently loadable and unchanged
    loaded_parent = Session.load(db=db, session_id=parent.id)
    assert loaded_parent.id == parent.id
    assert loaded_parent.parent_id is None

    # Messages seeded under parent are returned by get_messages
    msgs = db.get_messages(parent.id)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hello parent"
    assert msgs[1]["role"] == "assistant"

    # Branch session has no messages of its own yet
    branch_msgs = db.get_messages(branch.id)
    assert branch_msgs == []
