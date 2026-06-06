"""
Tests for FTS5 full-text search index on the messages table.

Covers:
- Index populated after INSERT (via messages_ai trigger)
- Index pruned after DELETE (via messages_ad trigger)
- Backfill of pre-existing rows via rebuild call in DB.__init__
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from aede.db import DB, DDL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path: Path) -> DB:
    return DB(tmp_path / "test.db")


def _insert_session(db: DB, session_id: str = "sess-1") -> None:
    db.insert_session(id=session_id, parent_id=None, title="Test", model="claude-test")


def _fts_match(db: DB, token: str) -> list[dict]:
    return db.con.execute(
        "SELECT content FROM messages_fts WHERE messages_fts MATCH ?",
        (token,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Task 1/2 — insert trigger
# ---------------------------------------------------------------------------

def test_fts_populated_after_insert(tmp_path):
    """After inserting a message, FTS MATCH should return it."""
    db = _make_db(tmp_path)
    _insert_session(db)
    db.insert_message(
        id="msg-1",
        session_id="sess-1",
        role="user",
        content="Hello xyzzy_unique_token world",
        token_count=5,
    )
    rows = _fts_match(db, "xyzzy_unique_token")
    assert len(rows) == 1
    assert "xyzzy_unique_token" in rows[0]["content"]


def test_fts_multiple_messages(tmp_path):
    """Multiple messages are all indexed."""
    db = _make_db(tmp_path)
    _insert_session(db)
    db.insert_message(id="m1", session_id="sess-1", role="user", content="apple fruit salad", token_count=3)
    db.insert_message(id="m2", session_id="sess-1", role="assistant", content="banana smoothie recipe", token_count=3)
    assert len(_fts_match(db, "apple")) == 1
    assert len(_fts_match(db, "banana")) == 1
    assert len(_fts_match(db, "nonexistent_zzzq")) == 0


# ---------------------------------------------------------------------------
# Task 3/4 — delete trigger
# ---------------------------------------------------------------------------

def test_fts_removed_after_delete(tmp_path):
    """After deleting a message row, it should no longer appear in FTS."""
    db = _make_db(tmp_path)
    _insert_session(db)
    db.insert_message(
        id="msg-del",
        session_id="sess-1",
        role="user",
        content="delete_me_token unique_xyz_987",
        token_count=3,
    )
    # Confirm it's in the index
    assert len(_fts_match(db, "delete_me_token")) == 1

    # Delete via raw SQL (no public delete API yet)
    db.con.execute("DELETE FROM messages WHERE id = ?", ("msg-del",))
    db.con.commit()

    # Should be gone from FTS
    assert len(_fts_match(db, "delete_me_token")) == 0


# ---------------------------------------------------------------------------
# Task 5/6 — backfill rebuild
# ---------------------------------------------------------------------------

def test_fts_backfill_existing_rows(tmp_path):
    """
    Simulate a 'legacy' DB: insert a message bypassing the FTS triggers by
    temporarily creating a raw connection without our DDL triggers, then
    reopen via DB() to trigger the rebuild — the row should now be searchable.
    """
    db_path = tmp_path / "legacy.db"

    # Write a minimal schema WITHOUT the FTS triggers (simulates old DB)
    raw = sqlite3.connect(str(db_path))
    raw.execute("PRAGMA journal_mode=WAL")
    raw.execute("PRAGMA foreign_keys=ON")
    # Create base tables
    raw.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, parent_id TEXT, title TEXT,
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
            model TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
        )
    """)
    raw.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL,
            created_at INTEGER NOT NULL, token_count INTEGER, compacted_at INTEGER
        )
    """)
    raw.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            content, content='messages', content_rowid='rowid'
        )
    """)
    # Insert data WITHOUT any triggers present
    import time
    now = int(time.time() * 1000)
    raw.execute(
        "INSERT INTO sessions VALUES (?,?,?,?,?,?,?)",
        ("s1", None, "Old session", now, now, "claude-test", "active"),
    )
    raw.execute(
        "INSERT INTO messages VALUES (?,?,?,?,?,?,?)",
        ("m1", "s1", "user", "legacy_token_backfill_test", now, 5, None),
    )
    raw.commit()
    raw.close()

    # FTS should be empty (no triggers were there)
    check = sqlite3.connect(str(db_path))
    check.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    rows_before = check.execute(
        "SELECT content FROM messages_fts WHERE messages_fts MATCH 'legacy_token_backfill_test'"
    ).fetchall()
    check.close()
    assert len(rows_before) == 0, "Expected empty FTS before rebuild"

    # Now open via DB() — the rebuild call should backfill
    db = DB(db_path)
    rows_after = _fts_match(db, "legacy_token_backfill_test")
    assert len(rows_after) == 1
    db.close()
