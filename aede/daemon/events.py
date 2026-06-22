from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WatchEvent:
    id: str
    path: str
    action: str
    label: str
    enabled: bool
    event_type: str = "watch"
    created_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "path": self.path,
            "action": self.action,
            "label": self.label,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class WebhookEvent:
    id: str
    route: str
    action: str
    label: str
    enabled: bool
    event_type: str = "webhook"
    created_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "route": self.route,
            "action": self.action,
            "label": self.label,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


class EventStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.db_path = data_dir / "daemon_events.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.db_path))
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          TEXT PRIMARY KEY,
                event_type  TEXT NOT NULL,
                path        TEXT,
                route       TEXT,
                action      TEXT NOT NULL,
                label       TEXT NOT NULL DEFAULT '',
                enabled     INTEGER NOT NULL DEFAULT 1,
                created_at  INTEGER NOT NULL
            )
        """)
        self.con.commit()

    def add_watch(
        self, path: str, action: str, label: str = ""
    ) -> WatchEvent:
        from ulid import ULID
        ev_id = str(ULID())
        now = int(time.time())
        self.con.execute(
            "INSERT INTO events (id, event_type, path, route, action, label, enabled, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (ev_id, "watch", path, None, action, label, 1, now),
        )
        self.con.commit()
        return WatchEvent(
            id=ev_id, path=path, action=action, label=label,
            enabled=True, created_at=now,
        )

    def add_webhook(
        self, route: str, action: str, label: str = ""
    ) -> WebhookEvent:
        from ulid import ULID
        ev_id = str(ULID())
        now = int(time.time())
        self.con.execute(
            "INSERT INTO events (id, event_type, path, route, action, label, enabled, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (ev_id, "webhook", None, route, action, label, 1, now),
        )
        self.con.commit()
        return WebhookEvent(
            id=ev_id, route=route, action=action, label=label,
            enabled=True, created_at=now,
        )

    def get_event(self, event_id: str) -> WatchEvent | WebhookEvent | None:
        row = self.con.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_event(row)

    def list_events(self) -> list[WatchEvent | WebhookEvent]:
        rows = self.con.execute(
            "SELECT * FROM events ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def delete_event(self, event_id: str) -> None:
        self.con.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.con.commit()

    def set_enabled(self, event_id: str, enabled: bool) -> None:
        self.con.execute(
            "UPDATE events SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, event_id),
        )
        self.con.commit()

    def get_events_by_type(self, event_type: str) -> list[WatchEvent | WebhookEvent]:
        rows = self.con.execute(
            "SELECT * FROM events WHERE event_type = ? AND enabled = 1 ORDER BY created_at DESC",
            (event_type,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def close(self) -> None:
        self.con.close()

    @staticmethod
    def _row_to_event(row: tuple) -> WatchEvent | WebhookEvent:
        ev_type = row[1]
        if ev_type == "watch":
            return WatchEvent(
                id=row[0], event_type=row[1], path=row[2] or "",
                action=row[4], label=row[5], enabled=bool(row[6]),
                created_at=row[7],
            )
        else:
            return WebhookEvent(
                id=row[0], event_type=row[1], route=row[3] or "",
                action=row[4], label=row[5], enabled=bool(row[6]),
                created_at=row[7],
            )
