from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Timer:
    id: str
    delay_s: int
    action: str
    label: str
    fire_at: int
    fired: bool
    created_at: int


class TimerStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.db_path = data_dir / "daemon_timers.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.db_path))
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS timers (
                id         TEXT PRIMARY KEY,
                delay_s    INTEGER NOT NULL,
                action     TEXT NOT NULL,
                label      TEXT NOT NULL DEFAULT '',
                fire_at    INTEGER NOT NULL,
                fired      INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)
        self.con.commit()

    def add_timer(
        self, delay_s: int, action: str, label: str = ""
    ) -> Timer:
        from ulid import ULID
        timer_id = str(ULID())
        now = int(time.time())
        fire_at = now + delay_s
        self.con.execute(
            "INSERT INTO timers (id, delay_s, action, label, fire_at, fired, created_at) VALUES (?,?,?,?,?,?,?)",
            (timer_id, delay_s, action, label, fire_at, 0, now),
        )
        self.con.commit()
        return Timer(
            id=timer_id, delay_s=delay_s, action=action, label=label,
            fire_at=fire_at, fired=False, created_at=now,
        )

    def get_timer(self, timer_id: str) -> Timer | None:
        row = self.con.execute(
            "SELECT * FROM timers WHERE id = ?", (timer_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_timer(row)

    def list_timers(self) -> list[Timer]:
        rows = self.con.execute(
            "SELECT * FROM timers ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_timer(r) for r in rows]

    def delete_timer(self, timer_id: str) -> None:
        self.con.execute("DELETE FROM timers WHERE id = ?", (timer_id,))
        self.con.commit()

    def mark_fired(self, timer_id: str) -> None:
        self.con.execute(
            "UPDATE timers SET fired = 1 WHERE id = ?", (timer_id,)
        )
        self.con.commit()

    def get_due_timers(self) -> list[Timer]:
        now = int(time.time())
        rows = self.con.execute(
            "SELECT * FROM timers WHERE fired = 0 AND fire_at <= ? ORDER BY fire_at ASC",
            (now,),
        ).fetchall()
        return [self._row_to_timer(r) for r in rows]

    def _set_fire_at(self, timer_id: str, fire_at: int) -> None:
        self.con.execute(
            "UPDATE timers SET fire_at = ? WHERE id = ?", (fire_at, timer_id)
        )
        self.con.commit()

    def close(self) -> None:
        self.con.close()

    @staticmethod
    def _row_to_timer(row: tuple) -> Timer:
        return Timer(
            id=row[0], delay_s=row[1], action=row[2], label=row[3],
            fire_at=row[4], fired=bool(row[5]), created_at=row[6],
        )
