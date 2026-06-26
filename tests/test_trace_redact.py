"""
Tests that TraceLogger and Rollout redact secrets before writing to JSONL.

Bug #65: trace/logger.py and rollout.py wrote raw tool args/results to JSONL
with 0 redact references — secrets landed in traces/ and sessions/ JSONL.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aede.observability.redact import redact_value
from aede.rollout import Rollout
from aede.trace.logger import TraceLogger

SAMPLE_ANTHROPIC_KEY = "sk-" + "ant-myrealapikey1234567890abcdef"
SAMPLE_GITHUB_TOKEN = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789abc"
SAMPLE_SLACK_TOKEN = "xoxb-" + "123456789012-1234567890123-abc123def456"


# ---------------------------------------------------------------------------
# Traces — T-REDACT-01x
# ---------------------------------------------------------------------------


class TestTraceLoggerRedactBeforeWrite:
    """T-REDACT-01x: TraceLogger must redact secrets in tool_calls / reasoning_text."""

    def test_redacts_tool_call_args(self, tmp_path):
        """A tool_call whose args contain an API key is written with <REDACTED>."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        tool_calls = [
            {"name": "bash", "args": {"cmd": "curl -H 'Authorization: Bearer %s'" % SAMPLE_ANTHROPIC_KEY}, "result": "ok", "duration_ms": 50},
        ]

        logger.write_turn_trace(
            session_id="sess_redact01",
            turn_number=0,
            input_tokens=10,
            output_tokens=5,
            cached_tokens=0,
            tool_calls=tool_calls,
            reasoning_text="used the api key directly, oops",
            outcome="tool_use",
        )

        lines = (traces_dir / "sess_redact01.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])

        raw = json.dumps(record)

        # Secret must NOT appear in the serialized JSONL
        assert SAMPLE_ANTHROPIC_KEY not in raw, "API key leaked into JSONL"
        # Record structure is intact
        assert record["session_id"] == "sess_redact01"
        assert record["turn_number"] == 0
        assert record["input_tokens"] == 10
        assert record["outcome"] == "tool_use"

    def test_redacts_tool_call_result(self, tmp_path):
        """A tool result containing a secret is redacted."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        tool_calls = [
            {"name": "gh_api", "args": {"endpoint": "/user"}, "result": "token=%s ok" % SAMPLE_GITHUB_TOKEN, "duration_ms": 30},
        ]

        logger.write_turn_trace(
            session_id="sess_redact02",
            turn_number=0,
            input_tokens=10,
            output_tokens=5,
            cached_tokens=0,
            tool_calls=tool_calls,
            reasoning_text="",
            outcome="tool_use",
        )

        record = json.loads((traces_dir / "sess_redact02.jsonl").read_text(encoding="utf-8"))
        raw = json.dumps(record)
        assert SAMPLE_GITHUB_TOKEN not in raw
        assert record["tool_calls"][0]["name"] == "gh_api"

    def test_redacts_reasoning_text(self, tmp_path):
        """reasoning_text that contains a secret is redacted."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        leaked_reasoning = "I found the Slack token: %s" % SAMPLE_SLACK_TOKEN

        logger.write_turn_trace(
            session_id="sess_redact03",
            turn_number=0,
            input_tokens=10,
            output_tokens=5,
            cached_tokens=0,
            tool_calls=[],
            reasoning_text=leaked_reasoning,
            outcome="end_turn",
        )

        record = json.loads((traces_dir / "sess_redact03.jsonl").read_text(encoding="utf-8"))
        raw = json.dumps(record)
        assert SAMPLE_SLACK_TOKEN not in raw
        assert record["session_id"] == "sess_redact03"

    def test_nonsecret_fields_intact(self, tmp_path):
        """session_id, turn_number, token counts, timestamp survive redaction unchanged."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_turn_trace(
            session_id="sess_redact04",
            turn_number=7,
            input_tokens=200,
            output_tokens=80,
            cached_tokens=15,
            tool_calls=[{"name": "simple", "args": {"safe_key": "safe_val"}, "result": "ok", "duration_ms": 10}],
            reasoning_text="nothing secret here",
            outcome="tool_use",
        )

        record = json.loads((traces_dir / "sess_redact04.jsonl").read_text(encoding="utf-8"))
        assert record["session_id"] == "sess_redact04"
        assert record["turn_number"] == 7
        assert record["input_tokens"] == 200
        assert record["output_tokens"] == 80
        assert record["cached_tokens"] == 15
        assert isinstance(record["timestamp"], int)
        assert record["schema_version"] == "phase2-draft"

    def test_write_event_payload_redacted(self, tmp_path):
        """write_event's payload is also redacted before JSONL write."""
        traces_dir = tmp_path / "traces"
        logger = TraceLogger(traces_dir=traces_dir)

        logger.write_event(
            session_id="sess_evt_redact",
            event_type="tool_result",
            payload={"token": SAMPLE_GITHUB_TOKEN, "result": "success"},
        )

        record = json.loads((traces_dir / "sess_evt_redact.jsonl").read_text(encoding="utf-8"))
        raw = json.dumps(record)
        assert SAMPLE_GITHUB_TOKEN not in raw
        assert record["event_type"] == "tool_result"
        assert record["session_id"] == "sess_evt_redact"


# ---------------------------------------------------------------------------
# Rollout — R-REDACT-01x
# ---------------------------------------------------------------------------


class TestRolloutRedactBeforeWrite:
    """R-REDACT-01x: Rollout must redact secrets in record before writing JSONL."""

    def test_redacts_secret_in_record(self, tmp_home):
        """A rollout record with an API key in a field is redacted before write."""
        r = Rollout(tmp_home / "data" / "sessions", "roll_redact01")
        r.write({"type": "tool_call", "tool_args": {"key": SAMPLE_ANTHROPIC_KEY}})

        files = list((tmp_home / "data" / "sessions").rglob("*.jsonl"))
        session_file = next(f for f in files if "roll_redact01" in f.name)
        contents = session_file.read_text(encoding="utf-8")
        record = json.loads(contents.splitlines()[0])

        raw = json.dumps(record)
        assert SAMPLE_ANTHROPIC_KEY not in raw, "API key leaked in rollout JSONL"
        assert record["v"] == 1
        assert "ts" in record
        assert record["type"] == "tool_call"

    def test_rollout_structure_preserved(self, tmp_home):
        """Rollout schema fields (v, ts, type) are preserved after redaction."""
        r = Rollout(tmp_home / "data" / "sessions", "roll_redact02")
        r.write({"type": "session_start", "session_id": "roll_redact02"})
        r.write({"type": "user_message", "content": "hello world"})

        files = list((tmp_home / "data" / "sessions").rglob("*.jsonl"))
        session_file = next(f for f in files if "roll_redact02" in f.name)
        lines = session_file.read_text(encoding="utf-8").splitlines()

        r1 = json.loads(lines[0])
        assert r1["v"] == 1
        assert r1["type"] == "session_start"
        assert r1["session_id"] == "roll_redact02"

        r2 = json.loads(lines[1])
        assert r2["v"] == 1
        assert r2["type"] == "user_message"
        assert r2["content"] == "hello world"

    def test_rollout_redacts_multiple_secrets(self, tmp_home):
        """Multiple secrets in one rollout record are all redacted."""
        r = Rollout(tmp_home / "data" / "sessions", "roll_redact03")
        r.write({
            "type": "tool_result",
            "tool_name": "bash",
            "args": {"cmd": "echo %s" % SAMPLE_ANTHROPIC_KEY},
            "result": "got token: %s" % SAMPLE_GITHUB_TOKEN,
        })

        files = list((tmp_home / "data" / "sessions").rglob("*.jsonl"))
        session_file = next(f for f in files if "roll_redact03" in f.name)
        raw = session_file.read_text(encoding="utf-8")
        assert SAMPLE_ANTHROPIC_KEY not in raw
        assert SAMPLE_GITHUB_TOKEN not in raw
