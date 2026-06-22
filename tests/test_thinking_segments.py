# tests/test_thinking_segments.py
"""Tests for thinking_segments DB table and CRUD methods."""
from pathlib import Path
from aede.db import DB
from aede.session import Session
from ulid import ULID


def test_insert_and_get_thinking_segments(tmp_path):
    db = DB(tmp_path / "t.db")
    s = Session.create(db, "claude-code", parent_id=None)
    mid = str(ULID())
    db.insert_message(id=mid, session_id=s.id, role="assistant", content="", token_count=None)

    db.insert_thinking_segment(message_id=mid, text="first thought", seq=0)
    db.insert_thinking_segment(message_id=mid, text="second thought", seq=2)

    result = db.get_thinking_segments_for_message_ids([mid])
    assert mid in result
    segs = result[mid]
    assert len(segs) == 2
    assert segs[0]["text"] == "first thought"
    assert segs[0]["seq"] == 0
    assert segs[1]["text"] == "second thought"
    assert segs[1]["seq"] == 2


def test_thinking_segments_ordered_by_seq(tmp_path):
    db = DB(tmp_path / "t.db")
    s = Session.create(db, "claude-code", parent_id=None)
    mid = str(ULID())
    db.insert_message(id=mid, session_id=s.id, role="assistant", content="", token_count=None)

    # Insert out of order
    db.insert_thinking_segment(message_id=mid, text="second", seq=2)
    db.insert_thinking_segment(message_id=mid, text="first", seq=0)

    result = db.get_thinking_segments_for_message_ids([mid])
    segs = result[mid]
    assert segs[0]["seq"] == 0
    assert segs[1]["seq"] == 2


def test_empty_message_ids_returns_empty(tmp_path):
    db = DB(tmp_path / "t.db")
    assert db.get_thinking_segments_for_message_ids([]) == {}


def test_get_segments_missing_message_id_returns_empty(tmp_path):
    db = DB(tmp_path / "t.db")
    result = db.get_thinking_segments_for_message_ids(["nonexistent"])
    assert result == {}


def test_existing_thinking_column_still_works(tmp_path):
    """Native provider single-blob thinking must not regress."""
    db = DB(tmp_path / "t.db")
    s = Session.create(db, "claude-3-5-sonnet", parent_id=None)
    mid = str(ULID())
    db.insert_message(id=mid, session_id=s.id, role="assistant", content="", token_count=None)
    db.update_message(id=mid, content="answer", token_count=10, thinking="single block")
    row = next(m for m in db.get_messages(s.id) if m["id"] == mid)
    assert row["thinking"] == "single block"
