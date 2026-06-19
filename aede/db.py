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
    status      TEXT NOT NULL DEFAULT 'active',
    project_dir TEXT,
    gate_mode   TEXT
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
CREATE TABLE IF NOT EXISTS thinking_segments (
    id          TEXT PRIMARY KEY,
    message_id  TEXT NOT NULL REFERENCES messages(id),
    text        TEXT NOT NULL,
    seq         INTEGER NOT NULL,
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
CREATE TABLE IF NOT EXISTS projects (
    id           TEXT PRIMARY KEY,
    project_dir  TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at   INTEGER NOT NULL,
    updated_at   INTEGER NOT NULL
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
CREATE TABLE IF NOT EXISTS learnings (
    id               TEXT PRIMARY KEY,
    type             TEXT NOT NULL,
    content          TEXT NOT NULL,
    source           TEXT NOT NULL,
    created_at       INTEGER NOT NULL,
    trusted          INTEGER NOT NULL DEFAULT 0,
    lower_trust      INTEGER NOT NULL DEFAULT 0,
    verifier_outcome TEXT,
    embedding        BLOB
);
CREATE VIRTUAL TABLE IF NOT EXISTS learnings_fts USING fts5(
    content,
    content='learnings',
    content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS learnings_ai AFTER INSERT ON learnings BEGIN
  INSERT INTO learnings_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS learnings_ad AFTER DELETE ON learnings BEGIN
  INSERT INTO learnings_fts(learnings_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER IF NOT EXISTS learnings_au AFTER UPDATE ON learnings BEGIN
  INSERT INTO learnings_fts(learnings_fts, rowid, content) VALUES('delete', old.rowid, old.content);
  INSERT INTO learnings_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TABLE IF NOT EXISTS docs (
    path    TEXT PRIMARY KEY,
    mtime   INTEGER NOT NULL,
    size    INTEGER NOT NULL,
    content TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    path UNINDEXED,
    content,
    content='docs',
    content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
  INSERT INTO docs_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, content) VALUES('delete', old.rowid, old.content);
  INSERT INTO docs_fts(rowid, content) VALUES (new.rowid, new.content);
END;
"""


def _now_ms() -> int:
    """Return the current UTC time as milliseconds since the epoch."""
    return int(time.time() * 1000)


def _normalize_path(path: str | None) -> str | None:
    """Normalize a filesystem path to use forward slashes.

    SQLite string comparison is exact, so on Windows a path stored with
    backslashes (from ``Path.cwd()``) won't match one with forward slashes
    (from the browser/web API).  Normalizing at the write boundary keeps
    lookups consistent regardless of the caller's platform or input source.
    """
    if path is None:
        return None
    return path.replace("\\", "/")


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
        # Rebuild learnings FTS index idempotently (same pattern as messages_fts)
        self.con.execute("INSERT INTO learnings_fts(learnings_fts) VALUES('rebuild')")
        self.con.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
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
        # WS-01 migration: add project_dir column to sessions if missing.
        try:
            self.con.execute("ALTER TABLE sessions ADD COLUMN project_dir TEXT")
            self.con.commit()
        except Exception:
            pass
        # PM-01 migration: add gate_mode column to sessions if missing.
        try:
            self.con.execute("ALTER TABLE sessions ADD COLUMN gate_mode TEXT")
            self.con.commit()
        except Exception:
            pass
        # PJ-01 migration: create projects table if missing (DB created before DDL had it).
        try:
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id           TEXT PRIMARY KEY,
                    project_dir  TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    created_at   INTEGER NOT NULL,
                    updated_at   INTEGER NOT NULL
                )
            """)
            self.con.commit()
        except Exception:
            pass
        # TH-01 migration: add thinking column to messages if missing.
        try:
            self.con.execute("ALTER TABLE messages ADD COLUMN thinking TEXT")
            self.con.commit()
        except Exception:
            pass
        # TD-01 migration: add turn_duration_ms column to messages if missing.
        try:
            self.con.execute("ALTER TABLE messages ADD COLUMN turn_duration_ms INTEGER")
            self.con.commit()
        except Exception:
            pass
        # RW-01 migration: add branch_message_id column to sessions if missing.
        try:
            self.con.execute("ALTER TABLE sessions ADD COLUMN branch_message_id TEXT")
            self.con.commit()
        except Exception:
            pass
        # Set row_factory after schema is created
        self.con.row_factory = _row_factory

    def insert_session(
        self,
        id: str,
        parent_id: str | None,
        title: str,
        model: str,
        project_dir: str | None = None,
        gate_mode: str | None = None,
        branch_message_id: str | None = None,
    ) -> None:
        """Insert a new session row with ``status='active'`` and timestamps set to now."""
        now = _now_ms()
        self.con.execute(
            "INSERT INTO sessions (id, parent_id, title, created_at, updated_at, model, project_dir, gate_mode, branch_message_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (id, parent_id, title, now, now, model, _normalize_path(project_dir), gate_mode, branch_message_id),
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

    def update_session_gate_mode(self, id: str, gate_mode: str | None) -> None:
        """Update the ``gate_mode`` field and refresh ``updated_at`` for the session."""
        self.con.execute(
            "UPDATE sessions SET gate_mode = ?, updated_at = ? WHERE id = ?",
            (gate_mode, _now_ms(), id),
        )
        self.con.commit()

    def delete_session(self, id: str) -> None:
        """Delete a session and all its associated messages, tool calls, and tokens.

        Relies on ON DELETE CASCADE if available, but for safety and because
        SQLite requires PRAGMA foreign_keys=ON (which we set), we handle it.
        Actually, we just delete the session and let FKs handle the rest if configured.
        """
        # Delete messages first to ensure triggers etc. are handled if necessary,
        # although with CASCADE it should be fine.
        # token_usage and messages both have REFERENCES sessions(id)
        # tool_calls references messages(id)
        
        # We don't have ON DELETE CASCADE in the DDL currently.
        # Let's check the DDL.
        self.con.execute("DELETE FROM token_usage WHERE session_id = ?", (id,))
        # tool_calls references messages, so delete them first
        self.con.execute(
            "DELETE FROM tool_calls WHERE message_id IN (SELECT id FROM messages WHERE session_id = ?)",
            (id,),
        )
        self.con.execute("DELETE FROM messages WHERE session_id = ?", (id,))
        self.con.execute("DELETE FROM sessions WHERE id = ?", (id,))
        self.con.commit()

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent sessions ordered by ``updated_at`` descending."""
        return self.con.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()

    def list_project_sessions(self, project_dir: str) -> list[dict[str, Any]]:
        """Return ALL sessions for a project directory, unlimited, ordered by updated_at DESC.

        Returns an empty list if ``project_dir`` is None or empty.
        """
        if not project_dir:
            return []
        return self.con.execute(
            "SELECT * FROM sessions WHERE project_dir = ? ORDER BY updated_at DESC",
            (project_dir,),
        ).fetchall()

    def list_global_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated sessions with no project_dir, plus total count.

        Returns:
            Tuple of (sessions_list, total_count).  Total is the number of
            rows *without* a project_dir, regardless of pagination.
        """
        total = self.con.execute(
            "SELECT COUNT(*) as cnt FROM sessions WHERE project_dir IS NULL"
        ).fetchone()["cnt"]
        rows = self.con.execute(
            "SELECT * FROM sessions WHERE project_dir IS NULL ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return rows, total

    def set_session_project_dir(self, id: str, project_dir: str) -> None:
        """Update the session's project directory."""
        self.con.execute(
            "UPDATE sessions SET project_dir = ?, updated_at = ? WHERE id = ?",
            (_normalize_path(project_dir), _now_ms(), id),
        )
        self.con.commit()

    def insert_project(
        self,
        id: str,
        project_dir: str,
        display_name: str,
    ) -> None:
        """Insert a new project row."""
        now = _now_ms()
        self.con.execute(
            "INSERT OR IGNORE INTO projects (id, project_dir, display_name, created_at, updated_at) VALUES (?,?,?,?,?)",
            (id, _normalize_path(project_dir), display_name, now, now),
        )
        self.con.commit()

    def list_projects(self) -> list[dict[str, Any]]:
        """Return all projects ordered by most recently updated."""
        return self.con.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        ).fetchall()

    def get_project(self, id: str) -> dict[str, Any] | None:
        """Return a project by its ID."""
        return self.con.execute(
            "SELECT * FROM projects WHERE id = ?", (id,)
        ).fetchone()

    def get_project_by_dir(self, project_dir: str) -> dict[str, Any] | None:
        """Return a project by its directory path."""
        return self.con.execute(
            "SELECT * FROM projects WHERE project_dir = ?", (_normalize_path(project_dir),)
        ).fetchone()

    def delete_project(self, id: str) -> None:
        """Delete a project (does not touch files on disk)."""
        self.con.execute("DELETE FROM projects WHERE id = ?", (id,))
        self.con.commit()

    def insert_message(
        self,
        id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int | None,
        thinking: str | None = None,
    ) -> None:
        """Persist one conversation message (user or assistant) to the DB."""
        self.con.execute(
            "INSERT INTO messages (id, session_id, role, content, created_at, token_count, thinking) VALUES (?,?,?,?,?,?,?)",
            (id, session_id, role, content, _now_ms(), token_count, thinking),
        )
        self.con.commit()

    def update_message(
        self,
        id: str,
        content: str,
        token_count: int | None,
        thinking: str | None = None,
    ) -> None:
        """Fill in a previously-inserted message's content/tokens/thinking.

        Assistant rows are inserted empty *before* the provider call so that
        tool calls reported mid-stream (notably ACP agents, which run tools in
        their subprocess and emit them during ``stream_turn``) have a valid
        ``message_id`` FK to persist against.  The finalized text is written
        here once the response completes.
        """
        self.con.execute(
            "UPDATE messages SET content=?, token_count=?, thinking=? WHERE id=?",
            (content, token_count, thinking, id),
        )
        self.con.commit()

    def set_message_duration(
        self,
        id: str,
        turn_duration_ms: int,
    ) -> None:
        """Persist the wall-clock turn duration (ms) onto an assistant message row.

        Called from the ``on_turn_done`` callback after ``run_turn`` completes,
        so it sets only ``turn_duration_ms`` without overwriting content/tokens.
        """
        self.con.execute(
            "UPDATE messages SET turn_duration_ms=? WHERE id=?",
            (turn_duration_ms, id),
        )
        self.con.commit()

    def delete_message(self, id: str) -> None:
        """Delete a message and its tool calls (used to clean up an empty
        assistant placeholder when the provider call fails)."""
        self.con.execute("DELETE FROM tool_calls WHERE message_id = ?", (id,))
        self.con.execute("DELETE FROM messages WHERE id = ?", (id,))
        self.con.commit()

    def delete_messages_after(
        self,
        session_id: str,
        timestamp_ms: int,
        boundary_id: str | None = None,
    ) -> int:
        """Delete every message in *session_id* strictly after *timestamp_ms*
        along with the tool_calls that belong to those messages, returning
        the number of messages removed.

        When *boundary_id* is provided, messages that share the same
        ``created_at`` as the boundary are tie-broken by ``id`` so the
        boundary message itself is always preserved — this is the path used
        by the in-place rewind endpoint, where two messages can land in the
        same millisecond on fast machines.

        When *boundary_id* is ``None``, deletion is purely a timestamp
        comparison (``created_at > timestamp_ms``); the boundary is whatever
        happens to carry that exact timestamp.
        """
        if boundary_id is not None:
            rows = self.con.execute(
                """
                SELECT id FROM messages
                WHERE session_id = ?
                  AND (created_at > ? OR (created_at = ? AND id > ?))
                """,
                (session_id, timestamp_ms, timestamp_ms, boundary_id),
            ).fetchall()
        else:
            rows = self.con.execute(
                "SELECT id FROM messages WHERE session_id = ? AND created_at > ?",
                (session_id, timestamp_ms),
            ).fetchall()
        if not rows:
            return 0
        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" for _ in ids)
        for mid in ids:
            self.delete_message(mid)
        return len(ids)

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

    def upsert_tool_call(
        self,
        id: str,
        message_id: str,
        tool_name: str,
        args: str,
        status: str,
    ) -> None:
        """Insert or update a tool call, preserving the original ``created_at``.

        ACP re-emits ``tool_call`` WS events (middle update with populated
        args, terminal update with ``_start_line``) for the same call ID;
        this avoids the PRIMARY KEY collision that a plain ``INSERT`` would
        trigger.
        """
        self.con.execute(
            "INSERT INTO tool_calls (id, message_id, tool_name, args, status, created_at) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "  tool_name=excluded.tool_name,"
            "  args=excluded.args,"
            "  status=excluded.status",
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

    def get_tool_calls_for_message_ids(self, message_ids: list[str]) -> dict[str, list[dict]]:
        if not message_ids:
            return {}
        import json
        placeholders = ",".join("?" for _ in message_ids)
        rows = self.con.execute(
            f"SELECT * FROM tool_calls WHERE message_id IN ({placeholders}) ORDER BY created_at ASC",
            message_ids,
        ).fetchall()
        result: dict[str, list[dict]] = {}
        for row in rows:
            r = dict(row)
            try:
                r["args"] = json.loads(r["args"])
            except (json.JSONDecodeError, TypeError):
                r["args"] = {}
            mid = r["message_id"]
            if mid not in result:
                result[mid] = []
            result[mid].append(r)
        return result

    def insert_thinking_segment(self, message_id: str, text: str, seq: int) -> None:
        """Persist one thinking segment for an assistant message (ACP path)."""
        import uuid
        self.con.execute(
            "INSERT INTO thinking_segments (id, message_id, text, seq, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), message_id, text, seq, _now_ms()),
        )
        self.con.commit()

    def get_thinking_segments_for_message_ids(self, message_ids: list[str]) -> dict[str, list[dict]]:
        """Return thinking segments keyed by message_id, ordered by seq ASC."""
        if not message_ids:
            return {}
        placeholders = ",".join("?" for _ in message_ids)
        rows = self.con.execute(
            f"SELECT * FROM thinking_segments WHERE message_id IN ({placeholders}) ORDER BY seq ASC",
            message_ids,
        ).fetchall()
        result: dict[str, list[dict]] = {}
        for row in rows:
            mid = row["message_id"]
            if mid not in result:
                result[mid] = []
            result[mid].append(dict(row))
        return result

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
        ),
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

    def search_messages(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Full-text search over message history using FTS5.

        For each hit, gathers a ±5 message context window (by insertion order
        within the session), plus session bookends (first and last message of
        the session), plus session metadata.  Overlapping context windows for
        hits in the same session are deduplicated.

        Args:
            query: FTS5 MATCH expression (e.g. a keyword or phrase).
            limit: Maximum number of hit messages to process.

        Returns:
            A list of result-group dicts, one per hit, each containing:
            ``session_id``, ``session_title``, ``session_created_at``,
            ``hit`` (the matching message dict), ``context`` (list of message
            dicts in the ±5 window, ordered by created_at), and ``bookends``
            (list containing the first and last message of the session,
            deduplicated with context).
        """
        # Find matching rows via FTS5, joined back to the messages table.
        hits = self.con.execute(
            """
            SELECT m.*
            FROM messages m
            JOIN messages_fts f ON m.rowid = f.rowid
            WHERE messages_fts MATCH ?
            ORDER BY m.created_at DESC
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()

        if not hits:
            return []

        results: list[dict[str, Any]] = []
        for hit in hits:
            session_id: str = hit["session_id"]

            # Fetch session metadata.
            session_row = self.con.execute(
                "SELECT id, title, created_at FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

            # Fetch all messages for this session ordered by created_at.
            all_msgs = self.con.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()

            # Locate the hit position in the ordered list.
            hit_idx = next(
                (i for i, m in enumerate(all_msgs) if m["id"] == hit["id"]),
                None,
            )
            if hit_idx is None:
                # Should not happen, but skip gracefully.
                continue

            # ±5 window.
            window_start = max(0, hit_idx - 5)
            window_end = min(len(all_msgs) - 1, hit_idx + 5)
            context_msgs = all_msgs[window_start : window_end + 1]

            # Bookends: first and last message of the session.
            bookend_ids = {all_msgs[0]["id"], all_msgs[-1]["id"]}
            context_ids = {m["id"] for m in context_msgs}
            bookends = [
                m for m in [all_msgs[0], all_msgs[-1]]
                if m["id"] not in context_ids
            ]
            # Deduplicate when first == last (single-message session).
            seen: set[str] = set()
            deduped_bookends: list[dict[str, Any]] = []
            for m in bookends:
                if m["id"] not in seen:
                    seen.add(m["id"])
                    deduped_bookends.append(m)

            results.append(
                {
                    "session_id": session_id,
                    "session_title": session_row["title"] if session_row else None,
                    "session_created_at": session_row["created_at"] if session_row else None,
                    "hit": hit,
                    "context": context_msgs,
                    "bookends": deduped_bookends,
                }
            )

        return results

    def insert_learning(
        self,
        id: str,
        type: str,
        content: str,
        source: str,
        trusted: bool = False,
        lower_trust: bool = False,
        verifier_outcome: str | None = None,
        embedding: bytes | None = None,
    ) -> None:
        """Insert one learning row into the learnings table.

        Args:
            id: ULID string for the learning.
            type: Learning category (anti-pattern, failed-approach, etc.).
            content: Free-text body.
            source: Origin (user, auto_learned, test_failure, tool_error).
            trusted: Whether the verifier has confirmed this learning.
            lower_trust: Whether this is a non-code learning pending full verification.
            verifier_outcome: Verifier result string, or None.
            embedding: Packed BLOB from struct.pack, or None if not embedded yet.
        """
        self.con.execute(
            """
            INSERT INTO learnings
                (id, type, content, source, created_at, trusted, lower_trust, verifier_outcome, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id, type, content, source, _now_ms(),
                int(trusted), int(lower_trust), verifier_outcome, embedding,
            ),
        )
        self.con.commit()

    def get_all_learnings(self) -> list[dict[str, Any]]:
        """Return all rows from the learnings table, ordered by created_at ascending."""
        return self.con.execute(
            "SELECT * FROM learnings ORDER BY created_at ASC"
        ).fetchall()

    def insert_doc(self, path: str, mtime: int, size: int, content: str) -> None:
        """Insert or replace a single docs row (path is the PK)."""
        self.con.execute(
            "INSERT OR REPLACE INTO docs (path, mtime, size, content) VALUES (?,?,?,?)",
            (path, mtime, size, content),
        )
        self.con.commit()

    def get_token_usage_detail(self, session_id: str) -> list[dict]:
        """Return per-turn token usage data for a session."""
        return self.con.execute(
            "SELECT turn_number, input_tokens, output_tokens, cached_tokens, role, created_at FROM token_usage WHERE session_id = ? ORDER BY turn_number ASC",
            (session_id,),
        ).fetchall()

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.con.close()
