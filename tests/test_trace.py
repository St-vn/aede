"""
Tests for aede.trace.logger — T-12x GEPA TraceLogger.

TDD: tests written FIRST.  Run before implementation to confirm RED.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from aede.trace.logger import TraceLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_tool_calls() -> list[dict]:
    return [
        {"name": "read_file", "args": {"path": "/tmp/x"}, "result": "ok", "duration_ms": 42},
        {"name": "web_search", "args": {"query": "foo"}, "result": "results...", "duration_ms": 300},
    ]


# ---------------------------------------------------------------------------
# T-12x — TraceLogger
# ---------------------------------------------------------------------------

class TestTraceLogger:
    """T-12x: write_turn_trace appends one JSON line per call."""

    def test_trace_written_to_jsonl(self, tmp_path):
        """write_turn_trace writes a record; reading back shows all fields + schema_version."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="sess_01",
            turn_number=1,
            input_tokens=100,
            output_tokens=50,
            cached_tokens=10,
            tool_calls=_sample_tool_calls(),
            reasoning_text="I decided to read the file first.",
            outcome="tool_use",
        )

        jsonl_path = traces_dir / "sess_01.jsonl"
        assert jsonl_path.exists(), "JSONL file must be created"

        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["session_id"] == "sess_01"
        assert record["turn_number"] == 1
        assert record["input_tokens"] == 100
        assert record["output_tokens"] == 50
        assert record["cached_tokens"] == 10
        assert record["tool_calls"] == _sample_tool_calls()
        assert record["reasoning_text"] == "I decided to read the file first."
        assert record["outcome"] == "tool_use"
        assert record["schema_version"] == "phase2-draft"
        assert "timestamp" in record
        assert isinstance(record["timestamp"], int)

    def test_second_write_appends(self, tmp_path):
        """Two write_turn_trace calls → two lines in the JSONL file."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="sess_02",
            turn_number=1,
            input_tokens=10,
            output_tokens=5,
            cached_tokens=0,
            tool_calls=[],
            reasoning_text="turn 1",
            outcome="end_turn",
        )
        logger.write_turn_trace(
            session_id="sess_02",
            turn_number=2,
            input_tokens=20,
            output_tokens=8,
            cached_tokens=2,
            tool_calls=[],
            reasoning_text="turn 2",
            outcome="end_turn",
        )

        jsonl_path = traces_dir / "sess_02.jsonl"
        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

        r1 = json.loads(lines[0])
        r2 = json.loads(lines[1])
        assert r1["turn_number"] == 1
        assert r2["turn_number"] == 2

    def test_creates_traces_dir_if_absent(self, tmp_path):
        """TraceLogger must create the traces directory on first write."""
        traces_dir = tmp_path / "nested" / "traces"
        assert not traces_dir.exists()

        logger = TraceLogger(traces_dir=traces_dir)
        logger.write_turn_trace(
            session_id="s",
            turn_number=0,
            input_tokens=1,
            output_tokens=1,
            cached_tokens=0,
            tool_calls=[],
            reasoning_text="",
            outcome="end_turn",
        )

        assert traces_dir.exists()

    def test_different_sessions_write_to_separate_files(self, tmp_path):
        """Each session_id gets its own <session_id>.jsonl file."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="alpha",
            turn_number=1,
            input_tokens=1, output_tokens=1, cached_tokens=0,
            tool_calls=[], reasoning_text="", outcome="end_turn",
        )
        logger.write_turn_trace(
            session_id="beta",
            turn_number=1,
            input_tokens=2, output_tokens=2, cached_tokens=0,
            tool_calls=[], reasoning_text="", outcome="end_turn",
        )

        assert (traces_dir / "alpha.jsonl").exists()
        assert (traces_dir / "beta.jsonl").exists()

        alpha_lines = (traces_dir / "alpha.jsonl").read_text(encoding="utf-8").splitlines()
        beta_lines = (traces_dir / "beta.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(alpha_lines) == 1
        assert len(beta_lines) == 1

    def test_timestamp_is_milliseconds(self, tmp_path):
        """timestamp field is a Unix millisecond integer (> 1e12)."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="ts_test",
            turn_number=1,
            input_tokens=1, output_tokens=1, cached_tokens=0,
            tool_calls=[], reasoning_text="", outcome="end_turn",
        )

        record = json.loads((traces_dir / "ts_test.jsonl").read_text(encoding="utf-8"))
        assert record["timestamp"] > 1_000_000_000_000  # year 2001+ in ms

    def test_schema_version_is_phase2_draft(self, tmp_path):
        """schema_version must equal exactly 'phase2-draft' (locked decision Q9)."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="sv_test",
            turn_number=1,
            input_tokens=1, output_tokens=1, cached_tokens=0,
            tool_calls=[], reasoning_text="", outcome="end_turn",
        )

        record = json.loads((traces_dir / "sv_test.jsonl").read_text(encoding="utf-8"))
        assert record["schema_version"] == "phase2-draft"

    def test_tool_calls_list_stored_intact(self, tmp_path):
        """tool_calls list (with name/args/result/duration_ms) is stored without modification."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)
        calls = _sample_tool_calls()

        logger.write_turn_trace(
            session_id="tc_test",
            turn_number=1,
            input_tokens=1, output_tokens=1, cached_tokens=0,
            tool_calls=calls,
            reasoning_text="", outcome="end_turn",
        )

        record = json.loads((traces_dir / "tc_test.jsonl").read_text(encoding="utf-8"))
        assert record["tool_calls"] == calls

    def test_empty_tool_calls_and_reasoning(self, tmp_path):
        """Empty tool_calls and empty reasoning_text are valid and stored correctly."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="empty_test",
            turn_number=1,
            input_tokens=0, output_tokens=0, cached_tokens=0,
            tool_calls=[],
            reasoning_text="",
            outcome="end_turn",
        )

        record = json.loads((traces_dir / "empty_test.jsonl").read_text(encoding="utf-8"))
        assert record["tool_calls"] == []
        assert record["reasoning_text"] == ""

    def test_tool_calls_carry_score_and_passed(self, tmp_path):
        """Each tool-call record in the trace carries score and passed fields for GEPA compat."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        tool_calls = [
            {"name": "read_file", "args": {"path": "/x"}, "result": "ok", "duration_ms": 10, "score": 1.0, "passed": True},
            {"name": "powershell", "args": {"cmd": "rm"}, "result": "error", "duration_ms": 5, "score": 0.0, "passed": False},
            {"name": "read_file", "args": {"path": "/x"}, "result": "ok", "duration_ms": 10, "score": 0.5, "passed": True},
        ]

        logger.write_turn_trace(
            session_id="gepa_test",
            turn_number=1,
            input_tokens=100, output_tokens=50, cached_tokens=0,
            tool_calls=tool_calls,
            reasoning_text="retried",
            outcome="tool_use",
        )

        record = json.loads((traces_dir / "gepa_test.jsonl").read_text(encoding="utf-8"))
        stored = record["tool_calls"]
        assert len(stored) == 3
        assert stored[0]["score"] == 1.0
        assert stored[0]["passed"] is True
        assert stored[1]["score"] == 0.0
        assert stored[1]["passed"] is False
        assert stored[2]["score"] == 0.5
        assert stored[2]["passed"] is True


# ---------------------------------------------------------------------------
# V-01x — TraceLogger.write_event
# ---------------------------------------------------------------------------


class TestTraceLoggerWriteEvent:
    """V-01x: write_event appends event-shaped records to the same JSONL."""

    def test_write_event_basic_shape(self, tmp_path):
        """write_event writes a record with kind='event', event_type, payload, timestamp, schema_version."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_event(
            session_id="sess_v01",
            event_type="wake_word_trigger",
            payload={"wake_word": "hey jarvis", "matched_text": "", "source": "browser"},
        )

        jsonl_path = traces_dir / "sess_v01.jsonl"
        assert jsonl_path.exists()

        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["session_id"] == "sess_v01"
        assert record["kind"] == "event"
        assert record["event_type"] == "wake_word_trigger"
        assert record["payload"] == {"wake_word": "hey jarvis", "matched_text": "", "source": "browser"}
        assert record["schema_version"] == "phase2-draft"
        assert "timestamp" in record
        assert isinstance(record["timestamp"], int)
        assert record["timestamp"] > 1_000_000_000_000

    def test_write_event_coexists_with_turn_records(self, tmp_path):
        """kind='event' and kind='turn_trace' records live in the same JSONL without conflict."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="mixed",
            turn_number=0,
            input_tokens=10, output_tokens=5, cached_tokens=0,
            tool_calls=[], reasoning_text="", outcome="end_turn",
        )
        logger.write_event(
            session_id="mixed",
            event_type="wake_word_trigger",
            payload={"wake_word": "hey", "matched_text": "", "source": "browser"},
        )
        logger.write_turn_trace(
            session_id="mixed",
            turn_number=1,
            input_tokens=20, output_tokens=10, cached_tokens=2,
            tool_calls=[], reasoning_text="", outcome="end_turn",
        )

        lines = (traces_dir / "mixed.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3

        records = [json.loads(l) for l in lines]
        # Existing turn records have no 'kind' field; event records have kind='event'
        assert "kind" not in records[0] or records[0]["kind"] in ("turn_trace",)
        assert records[1]["kind"] == "event"
        assert records[1]["event_type"] == "wake_word_trigger"
        assert "kind" not in records[2] or records[2]["kind"] in ("turn_trace",)

    def test_write_event_timestamp_precision(self, tmp_path):
        """write_event timestamp is a Unix ms integer (matching write_turn_trace convention)."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_event(
            session_id="ts_prec",
            event_type="test",
            payload={},
        )

        record = json.loads((traces_dir / "ts_prec.jsonl").read_text(encoding="utf-8"))
        assert isinstance(record["timestamp"], int)
        assert record["timestamp"] > 1_000_000_000_000

    def test_write_event_different_sessions_separate_files(self, tmp_path):
        """Each session_id goes to its own <id>.jsonl for events too."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_event(session_id="a", event_type="test", payload={})
        logger.write_event(session_id="b", event_type="test", payload={})

        assert (traces_dir / "a.jsonl").exists()
        assert (traces_dir / "b.jsonl").exists()

    def test_write_event_append_multiple(self, tmp_path):
        """Two write_event calls → two lines."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_event(session_id="mult", event_type="e1", payload={"n": 1})
        logger.write_event(session_id="mult", event_type="e2", payload={"n": 2})

        lines = (traces_dir / "mult.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["event_type"] == "e1"
        assert json.loads(lines[1])["event_type"] == "e2"

    def test_write_event_creates_traces_dir(self, tmp_path):
        """write_event creates the traces dir if it doesn't exist."""
        traces_dir = tmp_path / "deeply" / "nested" / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_event(session_id="cd", event_type="test", payload={})

        assert traces_dir.exists()
        assert (traces_dir / "cd.jsonl").exists()
