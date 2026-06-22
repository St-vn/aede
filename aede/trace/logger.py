"""
TraceLogger — GEPA (Generative Execution Path Audit) append-only turn logger.

Each agent turn is serialised as one JSON line into
``<traces_dir>/<session_id>.jsonl``.

Design constraints
------------------
- Append-only, crash-safe: one ``open(mode="a") + flush`` per write.
- No heavy imports at module level (json / pathlib / time are stdlib fine).
- ``schema_version`` is a placeholder string ``"phase2-draft"`` (locked
  decision Q9 — will be migrated when the schema stabilises).
- The traces directory is created on first use (``mkdir parents/exist_ok``).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


_SCHEMA_VERSION = "phase2-draft"


class TraceLogger:
    """Append-only JSONL logger for agent turn traces.

    Args:
        traces_dir: Directory where per-session ``.jsonl`` files are written.
            Created automatically if absent.
    """

    def __init__(self, traces_dir: Path) -> None:
        self._traces_dir: Path = traces_dir

    def write_turn_trace(
        self,
        *,
        session_id: str,
        turn_number: int,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        tool_calls: list[dict],
        reasoning_text: str,
        outcome: str,
    ) -> None:
        """Append one turn record to ``<traces_dir>/<session_id>.jsonl``.

        The file is opened in append mode so each call is crash-safe: a
        partial write does not corrupt previously written lines.

        Args:
            session_id: Unique identifier for the agent session.
            turn_number: Zero-based turn index within the session.
            input_tokens: Number of input tokens consumed by this turn.
            output_tokens: Number of output tokens produced by this turn.
            cached_tokens: Number of tokens read from the KV cache.
            tool_calls: List of tool-call records, each with keys
                ``name``, ``args``, ``result``, ``duration_ms``.
            reasoning_text: The model's chain-of-thought / reasoning text, if
                available.  Empty string if not applicable.
            outcome: Turn outcome string (e.g. ``"end_turn"``, ``"tool_use"``).
        """
        record: dict[str, Any] = {
            "session_id": session_id,
            "turn_number": turn_number,
            "timestamp": int(time.time() * 1000),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "tool_calls": tool_calls,
            "reasoning_text": reasoning_text,
            "outcome": outcome,
            "schema_version": _SCHEMA_VERSION,
        }

        self._traces_dir.mkdir(parents=True, exist_ok=True)
        dest: Path = self._traces_dir / f"{session_id}.jsonl"
        with dest.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()

    def write_event(
        self,
        *,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Append an event record to ``<traces_dir>/<session_id>.jsonl``.

        Event records are distinguished from turn-trace records by the
        ``kind: "event"`` field.  Writes to the same file as
        :meth:`write_turn_trace`, preserving the append-only invariant.

        Args:
            session_id: Unique identifier for the agent session.
            event_type: Machine-readable event type (e.g. ``"wake_word_trigger"``).
            payload: Free-form event payload as a JSON-serialisable dict.
        """
        record: dict[str, Any] = {
            "session_id": session_id,
            "kind": "event",
            "event_type": event_type,
            "payload": payload,
            "timestamp": int(time.time() * 1000),
            "schema_version": _SCHEMA_VERSION,
        }

        self._traces_dir.mkdir(parents=True, exist_ok=True)
        dest: Path = self._traces_dir / f"{session_id}.jsonl"
        with dest.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
