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
