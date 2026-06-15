from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CronJob:
    id: str
    schedule: str
    action: str
    label: str
    enabled: bool
    last_run_at: int | None
    created_at: int


class CronStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.db_path = data_dir / "daemon_cron.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.db_path))
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS cron_jobs (
                id          TEXT PRIMARY KEY,
                schedule    TEXT NOT NULL,
                action      TEXT NOT NULL,
                label       TEXT NOT NULL DEFAULT '',
                enabled     INTEGER NOT NULL DEFAULT 1,
                last_run_at INTEGER,
                created_at  INTEGER NOT NULL
            )
        """)
        self.con.commit()

    def add_job(
        self, schedule: str, action: str, label: str = ""
    ) -> CronJob:
        from ulid import ULID
        job_id = str(ULID())
        now = int(time.time())
        self.con.execute(
            "INSERT INTO cron_jobs (id, schedule, action, label, enabled, last_run_at, created_at) VALUES (?,?,?,?,?,?,?)",
            (job_id, schedule, action, label, 1, None, now),
        )
        self.con.commit()
        return CronJob(
            id=job_id, schedule=schedule, action=action, label=label,
            enabled=True, last_run_at=None, created_at=now,
        )

    def get_job(self, job_id: str) -> CronJob | None:
        row = self.con.execute(
            "SELECT * FROM cron_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def list_jobs(self) -> list[CronJob]:
        rows = self.con.execute(
            "SELECT * FROM cron_jobs ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def delete_job(self, job_id: str) -> None:
        self.con.execute("DELETE FROM cron_jobs WHERE id = ?", (job_id,))
        self.con.commit()

    def set_enabled(self, job_id: str, enabled: bool) -> None:
        self.con.execute(
            "UPDATE cron_jobs SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, job_id),
        )
        self.con.commit()

    def get_enabled_jobs(self) -> list[CronJob]:
        rows = self.con.execute(
            "SELECT * FROM cron_jobs WHERE enabled = 1 ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def set_last_run(self, job_id: str, timestamp: int) -> None:
        self.con.execute(
            "UPDATE cron_jobs SET last_run_at = ? WHERE id = ?",
            (timestamp, job_id),
        )
        self.con.commit()

    def close(self) -> None:
        self.con.close()

    @staticmethod
    def _row_to_job(row: tuple) -> CronJob:
        return CronJob(
            id=row[0], schedule=row[1], action=row[2], label=row[3],
            enabled=bool(row[4]),
            last_run_at=row[5] if row[5] is not None else None,
            created_at=row[6],
        )
