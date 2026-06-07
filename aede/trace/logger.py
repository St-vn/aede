from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


class TraceLogger:
    """Append-only JSONL logger for turn-level traces."""

    def __init__(self, log_dir: Path) -> None:
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def write_turn_trace(
        self,
        session_id: str,
        turn_number: int,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        tool_calls: list[dict[str, Any]],
        reasoning_text: str,
        outcome: str,
    ) -> None:
        record = {
            "session_id": session_id,
            "turn_number": turn_number,
            "timestamp": int(time.time() * 1000),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "tool_calls": tool_calls,
            "reasoning_text": reasoning_text,
            "outcome": outcome,
            "schema_version": "phase2-draft",
        }
        trace_path = self._log_dir / f"{session_id}.jsonl"
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
