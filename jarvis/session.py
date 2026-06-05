from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any
from ulid import ULID


def generate_session_id() -> str:
    return str(ULID())


def make_title(first_message: str) -> str:
    msg = first_message.strip()
    if len(msg) < 10:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        return f"{msg} · {ts}"
    return msg[:60]


class Session:
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
        sid = generate_session_id()
        db.insert_session(id=sid, parent_id=parent_id, title=title or "", model=model)
        return cls.load(db=db, session_id=sid)

    @classmethod
    def load(cls, db: Any, session_id: str) -> "Session":
        row = db.get_session(session_id)
        if row is None:
            raise KeyError(f"Session not found: {session_id}")
        return cls(row)

    @classmethod
    def list_recent(cls, db: Any, limit: int = 20) -> list["Session"]:
        rows = db.list_sessions(limit=limit)
        return [cls(r) for r in rows]

    def set_title(self, db: Any, title: str) -> None:
        db.con.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, int(time.time() * 1000), self.id),
        )
        db.con.commit()
        self.title = title

    def archive(self, db: Any) -> None:
        db.update_session_status(self.id, "archived")
        self.status = "archived"

    def set_active(self, db: Any) -> None:
        db.update_session_status(self.id, "active")
        self.status = "active"
