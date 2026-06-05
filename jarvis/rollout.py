from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path


class Rollout:
    def __init__(self, sessions_dir: Path, session_id: str) -> None:
        now = datetime.now(timezone.utc)
        day_dir = sessions_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        self._path = day_dir / f"rollout-{session_id}.jsonl"

    def write(self, record: dict) -> None:
        record = {"v": 1, "ts": int(time.time() * 1000), **record}
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
