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
    created_at      INTEGER NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='rowid'
);
"""


def _now_ms() -> int:
    return int(time.time() * 1000)


def _row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


class DB:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path), check_same_thread=False)
        # Execute pragma statements
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA foreign_keys=ON")
        # Execute DDL statements - split by ; and filter empty lines
        for stmt in DDL.split(";"):
            stmt = stmt.strip()
            if stmt:
                self.con.execute(stmt)
        self.con.commit()
        # Set row_factory after schema is created
        self.con.row_factory = _row_factory

    def insert_session(
        self,
        id: str,
        parent_id: str | None,
        title: str,
        model: str,
    ) -> None:
        now = _now_ms()
        self.con.execute(
            "INSERT INTO sessions (id, parent_id, title, created_at, updated_at, model) VALUES (?,?,?,?,?,?)",
            (id, parent_id, title, now, now, model),
        )
        self.con.commit()

    def get_session(self, id: str) -> dict[str, Any] | None:
        return self.con.execute(
            "SELECT * FROM sessions WHERE id = ?", (id,)
        ).fetchone()

    def update_session_status(self, id: str, status: str) -> None:
        self.con.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now_ms(), id),
        )
        self.con.commit()

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
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
        self.con.execute(
            "INSERT INTO messages (id, session_id, role, content, created_at, token_count) VALUES (?,?,?,?,?,?)",
            (id, session_id, role, content, _now_ms(), token_count),
        )
        self.con.commit()

    def get_messages(
        self, session_id: str, include_compacted: bool = False
    ) -> list[dict[str, Any]]:
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
    ) -> None:
        self.con.execute(
            "INSERT INTO token_usage (id, session_id, turn_number, input_tokens, output_tokens, cached_tokens, created_at) VALUES (?,?,?,?,?,?,?)",
            (id, session_id, turn_number, input_tokens, output_tokens, cached_tokens, _now_ms()),
        )
        self.con.commit()

    def get_token_totals(self, session_id: str) -> dict[str, int]:
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
        self.con.close()
