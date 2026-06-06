"""
SQLite persistence layer for aede.

Maintains tables for sessions, messages, tool calls, and token usage using
WAL mode and foreign-key enforcement.  An FTS5 virtual table on messages
supports future full-text search.  All query methods return plain dicts via
a custom row factory.
"""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Any


DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    parent_id   TEXT REFERENCES sessions(id),
    title       TEXT,
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL,
    model       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(id),
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    created_at   INTEGER NOT NULL,
    token_count  INTEGER,
    compacted_at INTEGER
);
CREATE TABLE IF NOT EXISTS tool_calls (
    id          TEXT PRIMARY KEY,
    message_id  TEXT NOT NULL REFERENCES messages(id),
    tool_name   TEXT NOT NULL,
    args        TEXT NOT NULL,
    result      TEXT,
    status      TEXT NOT NULL,
    duration_ms INTEGER,
    created_at  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS token_usage (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    turn_number     INTEGER NOT NULL,
    input_tokens    INTEGER NOT NULL,
    output_tokens   INTEGER NOT NULL,
    cached_tokens   INTEGER NOT NULL DEFAULT 0,
    created_at      INTEGER NOT NULL,
    role            TEXT NOT NULL DEFAULT 'agent'
);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
  INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.rowid, old.content);
  INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;
"""


def _now_ms() -> int:
    """Return the current UTC time as milliseconds since the epoch."""
    return int(time.time() * 1000)


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    """sqlite3 row factory that returns each row as a ``{column: value}`` dict."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


class DB:
    """Thin wrapper around a SQLite connection providing typed CRUD helpers.

    The database is created (with schema) on first use.  The connection is kept
    open for the life of the process; call ``close()`` on shutdown.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path), check_same_thread=False)
        # Pragmas must be set before executescript (executescript does an implicit COMMIT)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA foreign_keys=ON")
        self.con.commit()
        # Execute full DDL (tables + FTS virtual table + sync triggers).
        # executescript is used because trigger bodies contain semicolons inside
        # BEGIN...END blocks, which the simple split(";") approach cannot handle.
        self.con.executescript(DDL)
        # Rebuild FTS index idempotently to backfill any pre-existing rows
        # (cheap at personal scale; external-content FTS5 requires explicit sync)
        self.con.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
        self.con.commit()
        # BC-06 migration: add role column to token_usage if it is missing.
        # SQLite does not support IF NOT EXISTS on ADD COLUMN — use try/except.
        try:
            self.con.execute(
                "ALTER TABLE token_usage ADD COLUMN role TEXT NOT NULL DEFAULT 'agent'"
            )
            self.con.commit()
        except Exception:
            pass  # Column already exists — idempotent
        # Set row_factory after schema is created
        self.con.row_factory = _row_factory

    def insert_session(
        self,
        id: str,
        parent_id: str | None,
        title: str,
        model: str,
    ) -> None:
        """Insert a new session row with ``status='active'`` and timestamps set to now."""
        now = _now_ms()
        self.con.execute(
            "INSERT INTO sessions (id, parent_id, title, created_at, updated_at, model) VALUES (?,?,?,?,?,?)",
            (id, parent_id, title, now, now, model),
        )
        self.con.commit()

    def get_session(self, id: str) -> dict[str, Any] | None:
        """Return the session row for ``id``, or ``None`` if not found."""
        return self.con.execute(
            "SELECT * FROM sessions WHERE id = ?", (id,)
        ).fetchone()

    def update_session_status(self, id: str, status: str) -> None:
        """Update the ``status`` field and refresh ``updated_at`` for the session."""
        self.con.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now_ms(), id),
        )
        self.con.commit()

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent sessions ordered by ``updated_at`` descending."""
        return self.con.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()

    def insert_message(
        self,
        id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int | None,
    ) -> None:
        """Persist one conversation message (user or assistant) to the DB."""
        self.con.execute(
            "INSERT INTO messages (id, session_id, role, content, created_at, token_count) VALUES (?,?,?,?,?,?)",
            (id, session_id, role, content, _now_ms(), token_count),
        )
        self.con.commit()

    def get_messages(
        self, session_id: str, include_compacted: bool = False
    ) -> list[dict[str, Any]]:
        """Return messages for a session ordered by creation time.

        By default excludes rows that have been marked compacted.  Pass
        ``include_compacted=True`` to include them.
        """
        if include_compacted:
            return self.con.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return self.con.execute(
            "SELECT * FROM messages WHERE session_id = ? AND compacted_at IS NULL ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()

    def mark_messages_compacted(self, message_ids: list[str]) -> None:
        """Set ``compacted_at`` to now for the given message IDs."""
        now = _now_ms()
        self.con.executemany(
            "UPDATE messages SET compacted_at = ? WHERE id = ?",
            [(now, mid) for mid in message_ids],
        )
        self.con.commit()

    def insert_tool_call(
        self,
        id: str,
        message_id: str,
        tool_name: str,
        args: str,
        status: str,
    ) -> None:
        """Record a tool invocation (without result) immediately after dispatch."""
        self.con.execute(
            "INSERT INTO tool_calls (id, message_id, tool_name, args, status, created_at) VALUES (?,?,?,?,?,?)",
            (id, message_id, tool_name, args, status, _now_ms()),
        )
        self.con.commit()

    def update_tool_call(
        self,
        id: str,
        result: str,
        status: str,
        duration_ms: int,
    ) -> None:
        """Fill in the result, final status, and wall-clock duration after a tool returns."""
        self.con.execute(
            "UPDATE tool_calls SET result=?, status=?, duration_ms=? WHERE id=?",
            (result, status, duration_ms, id),
        )
        self.con.commit()

    def insert_token_usage(
        self,
        id: str,
        session_id: str,
        turn_number: int,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        role: str = "agent",
    ) -> None:
        """Append one token-usage row for a completed LLM turn."""
        self.con.execute(
            "INSERT INTO token_usage (id, session_id, turn_number, input_tokens, output_tokens, cached_tokens, created_at, role) VALUES (?,?,?,?,?,?,?,?)",
            (id, session_id, turn_number, input_tokens, output_tokens, cached_tokens, _now_ms(), role),
        )
        self.con.commit()

    def get_token_totals(self, session_id: str) -> dict[str, int]:
        """Return summed ``{input_tokens, output_tokens, cached_tokens}`` for the session."""
        row = self.con.execute(
            "SELECT SUM(input_tokens) as input_tokens, SUM(output_tokens) as output_tokens, SUM(cached_tokens) as cached_tokens FROM token_usage WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return {
            "input_tokens": row["input_tokens"] or 0,
            "output_tokens": row["output_tokens"] or 0,
            "cached_tokens": row["cached_tokens"] or 0,
        }

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.con.close()
