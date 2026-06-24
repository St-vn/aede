from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

from aede.observability.redact import redact_value


_SCHEMA_VERSION = "fde-v1"


class FdeCapture:
    def __init__(
        self,
        enabled: bool = False,
        data_dir: Path = Path("."),
        endpoint: str | None = None,
        max_result_length: int = 4096,
    ) -> None:
        self._enabled = enabled
        self._data_dir = data_dir
        self._endpoint = endpoint
        self._max_result_length = max_result_length

    def capture_tool_call(
        self,
        *,
        session_id: str,
        turn_number: int,
        tool_name: str,
        tool_args: Any,
        tool_result: Any,
        outcome: str,
        latency_ms: float,
    ) -> None:
        if not self._enabled:
            return

        redacted_args = redact_value(tool_args) if tool_args is not None else None
        redacted_result = redact_value(tool_result) if tool_result is not None else None

        if isinstance(redacted_result, str) and len(redacted_result) > self._max_result_length:
            redacted_result = redacted_result[: self._max_result_length] + "..."

        record: dict[str, Any] = {
            "session_id": session_id,
            "turn_number": turn_number,
            "timestamp": int(time.time() * 1000),
            "tool_name": tool_name,
            "tool_args": redacted_args,
            "tool_result": redacted_result,
            "outcome": outcome,
            "latency_ms": latency_ms,
            "schema_version": _SCHEMA_VERSION,
        }

        fde_dir = self._data_dir / "fde"
        fde_dir.mkdir(parents=True, exist_ok=True)
        dest = fde_dir / f"{session_id}.jsonl"
        with dest.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()

    def try_upload(self, session_id: str) -> None:
        if not self._endpoint:
            return

        fde_dir = self._data_dir / "fde"
        src = fde_dir / f"{session_id}.jsonl"
        if not src.exists():
            return

        try:
            import httpx

            lines = src.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines]
            with httpx.Client() as client:
                client.post(self._endpoint, json={"session_id": session_id, "records": records}, timeout=10)
        except Exception:
            _log.debug("FDE upload failed", exc_info=True)
