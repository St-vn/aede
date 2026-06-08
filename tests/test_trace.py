import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_trace_written_to_jsonl(tmp_path):
    """TraceLogger writes a JSONL line to the trace file."""
    from aede.trace.logger import TraceLogger

    log_dir = tmp_path / "traces"
    log_dir.mkdir()
    logger = TraceLogger(log_dir=log_dir)

    logger.write_turn_trace(
        session_id="session-001",
        turn_number=1,
        input_tokens=100,
        output_tokens=50,
        cached_tokens=20,
        tool_calls=[{"name": "read_file", "args": {"path": "x.txt"}, "result": "ok", "duration_ms": 10}],
        reasoning_text="I need to read the file",
        outcome="completed",
    )

    trace_file = log_dir / "session-001.jsonl"
    assert trace_file.exists()

    lines = trace_file.read_text().strip().split("\n")
    assert len(lines) == 1

    data = json.loads(lines[0])
    assert data["session_id"] == "session-001"
    assert data["turn_number"] == 1
    assert data["input_tokens"] == 100
    assert data["output_tokens"] == 50
    assert data["cached_tokens"] == 20
    assert len(data["tool_calls"]) == 1
    assert data["outcome"] == "completed"
    assert data["schema_version"] == "phase2-draft"
    assert "timestamp" in data


def test_trace_append_only(tmp_path):
    """Multiple traces append to the same file."""
    from aede.trace.logger import TraceLogger

    log_dir = tmp_path / "traces"
    log_dir.mkdir()
    logger = TraceLogger(log_dir=log_dir)

    logger.write_turn_trace("s1", 1, 10, 5, 0, [], "thinking", "completed")
    logger.write_turn_trace("s1", 2, 20, 10, 0, [], "thinking", "completed")

    lines = (log_dir / "s1.jsonl").read_text().strip().split("\n")
    assert len(lines) == 2
