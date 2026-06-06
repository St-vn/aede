"""
Append-only JSONL rollout log for Jarvis sessions.

Every significant event (session start/end, user and assistant messages, tool
calls and results, compaction) is appended as a versioned JSON line to a daily
file under ``~/.jarvis/data/sessions/YYYY/MM/DD/rollout-<session_id>.jsonl``.
This provides a full audit trail independent of the SQLite database.
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path


class Rollout:
    """Writer for the per-session JSONL rollout log.

    The log file is created lazily on the first ``write`` call and placed in a
    ``YYYY/MM/DD`` subdirectory of ``sessions_dir`` based on the session's
    start date (UTC).
    """

    def __init__(self, sessions_dir: Path, session_id: str) -> None:
        now = datetime.now(timezone.utc)
        day_dir = sessions_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        self._path = day_dir / f"rollout-{session_id}.jsonl"

    def write(self, record: dict) -> None:
        """Append ``record`` to the log, injecting a schema version and UTC timestamp."""
        record = {"v": 1, "ts": int(time.time() * 1000), **record}
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
