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
        self.branch_message_id: str | None = data.get("branch_message_id")
        self.title: str | None = data.get("title")
        self.model: str = data["model"]
        self.status: str = data["status"]
        self.created_at: int = data["created_at"]
        self.updated_at: int = data["updated_at"]
        self.project_dir: str | None = data.get("project_dir")
        self.gate_mode: str | None = data.get("gate_mode")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "branch_message_id": self.branch_message_id,
            "title": self.title,
            "model": self.model,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "project_dir": self.project_dir,
            "gate_mode": self.gate_mode,
        }

    @classmethod
    def create(
        cls,
        db: Any,
        model: str,
        parent_id: str | None,
        title: str | None = None,
        project_dir: str | None = None,
        gate_mode: str | None = None,
    ) -> "Session":
        """Insert a new session row and return the loaded ``Session`` object."""
        sid = generate_session_id()
        db.insert_session(
            id=sid,
            parent_id=parent_id,
            title=title or "",
            model=model,
            project_dir=project_dir,
            gate_mode=gate_mode,
        )
        return cls.load(db=db, session_id=sid)

    def set_project_dir(self, db: Any, project_dir: str) -> None:
        """Update the session's project directory."""
        db.set_session_project_dir(self.id, project_dir)
        self.project_dir = project_dir

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

    def delete(self, db: Any) -> None:
        """Permanently delete this session and all its data from the DB."""
        db.delete_session(self.id)

    def set_active(self, db: Any) -> None:
        """Mark the session as active in the DB and update local state."""
        db.update_session_status(self.id, "active")
        self.status = "active"

    @classmethod
    def fork_from_message(cls, db: Any, parent_id: str, message_id: str) -> "Session":
        """Create a new session as a branch of *parent_id*, rooted at *message_id*.

        The new session inherits the parent's model, sets ``parent_id`` and
        ``branch_message_id``, and loads its message history from the parent
        chain truncated to the branch point.
        """
        parent = cls.load(db, parent_id)
        s = cls.create(db, parent.model, parent_id=parent_id)
        db.con.execute(
            "UPDATE sessions SET branch_message_id = ? WHERE id = ?",
            (message_id, s.id),
        )
        db.con.commit()
        return cls.load(db, s.id)

    @classmethod
    def truncate_after_message(cls, db: Any, session_id: str, message_id: str) -> "Session":
        """Delete every message in *session_id* that comes after *message_id*
        in the conversation sequence, then return the same session.

        Unlike :meth:`fork_from_message`, the session id is preserved — this
        is the in-place rewind used to erase a tail of conversation from the
        current branch.
        """
        session = cls.load(db, session_id)
        row = db.con.execute(
            "SELECT created_at FROM messages WHERE id = ? AND session_id = ?",
            (message_id, session_id),
        ).fetchone()
        if row is None:
            raise KeyError(f"Message not found: {message_id}")
        db.delete_messages_after(session_id, int(row["created_at"]), boundary_id=message_id)
        now = int(time.time() * 1000)
        db.con.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        db.con.commit()
        return session

    def set_gate_mode(self, db: Any, gate_mode: str | None) -> None:
        """Update the session's permission mode and refresh local state."""
        db.update_session_gate_mode(self.id, gate_mode)
        self.gate_mode = gate_mode
