"""
Session model for aede.

A Session is the top-level unit of conversation history in the DB.  Each run
of the CLI creates a new Session (or resumes an existing one).  Sessions can
be nested via ``parent_id`` for sub-agent flows.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any
from ulid import ULID


def generate_session_id() -> str:
    """Generate a new ULID-based session identifier."""
    return str(ULID())


def make_title(first_message: str) -> str:
    """Derive a session title from the first user message.

    Short messages (< 10 chars) are appended with a UTC timestamp for
    disambiguation.  Longer messages are truncated to 60 characters.
    """
    msg = first_message.strip()
    if len(msg) < 10:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        return f"{msg} · {ts}"
    return msg[:60]


class Session:
    """In-memory representation of an aede session loaded from the DB.

    Use the class methods ``create``, ``load``, and ``list_recent`` to
    construct instances — do not call the constructor directly.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data["id"]
        self.parent_id: str | None = data.get("parent_id")
        self.title: str | None = data.get("title")
        self.model: str = data["model"]
        self.status: str = data["status"]
        self.created_at: int = data["created_at"]
        self.updated_at: int = data["updated_at"]

    @classmethod
    def create(
        cls,
        db: Any,
        model: str,
        parent_id: str | None,
        title: str | None = None,
    ) -> "Session":
        """Insert a new session row and return the loaded ``Session`` object."""
        sid = generate_session_id()
        db.insert_session(id=sid, parent_id=parent_id, title=title or "", model=model)
        return cls.load(db=db, session_id=sid)

    @classmethod
    def load(cls, db: Any, session_id: str) -> "Session":
        """Load an existing session by ID.

        Raises:
            KeyError: if no session with ``session_id`` exists in the DB.
        """
        row = db.get_session(session_id)
        if row is None:
            raise KeyError(f"Session not found: {session_id}")
        return cls(row)

    @classmethod
    def list_recent(cls, db: Any, limit: int = 20) -> list["Session"]:
        """Return the most recent sessions ordered by last update, newest first."""
        rows = db.list_sessions(limit=limit)
        return [cls(r) for r in rows]

    def set_title(self, db: Any, title: str) -> None:
        """Update the session title in the DB and on this object."""
        db.con.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, int(time.time() * 1000), self.id),
        )
        db.con.commit()
        self.title = title

    def archive(self, db: Any) -> None:
        """Mark the session as archived in the DB and update local state."""
        db.update_session_status(self.id, "archived")
        self.status = "archived"

    def set_active(self, db: Any) -> None:
        """Mark the session as active in the DB and update local state."""
        db.update_session_status(self.id, "active")
        self.status = "active"
