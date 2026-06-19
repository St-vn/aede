"""
Integration tests for AgentLoop — T-15 (learnings suffix injection) and
T-13x (per-turn GEPA trace write).

TDD: tests written FIRST.  Run before implementation to confirm RED.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers shared by both test groups
# ---------------------------------------------------------------------------

def _make_cfg(tmp_path: Path):
    from aede.config import AedeConfig
    return AedeConfig(
        {
            "model": "claude-sonnet-4-20250514",
            "shell": "powershell",
            "tool_output_max_tokens": 8000,
            "context_window": 200000,
            "compaction_threshold": 0.85,
            "batch_approval_max": 5,
        },
        home=tmp_path,
    )


def _make_loop(tmp_path: Path):
    """Build a minimal AgentLoop for integration tests."""
    from aede.agent import AgentLoop

    cfg = _make_cfg(tmp_path)
    # Override data_dir so traces land in tmp_path/data
    cfg.data_dir = tmp_path / "data"

    loop = AgentLoop.__new__(AgentLoop)
    loop._cfg = cfg
    loop._session = MagicMock(id="test-session-001")
    loop._db = MagicMock()
    loop._rollout = MagicMock()
    loop._router = MagicMock()
    loop._router.validate_name = MagicMock()
    loop._router.validate_args = MagicMock()
    loop._router.requires_approval = MagicMock(return_value=False)
    loop._router.execute_sync = MagicMock()
    loop._router.anthropic_tool_schemas = MagicMock(return_value=[])
    loop._gate_store = MagicMock()
    loop._gate_store.is_allowed = MagicMock(return_value=True)
    loop._tracker = MagicMock()
    loop._tracker.record = MagicMock()
    loop._console = MagicMock()
    loop._project_dir = tmp_path
    loop._messages = []
    loop._turn = 0
    loop._provider = None
    loop._system_prompt = None
    loop._stream_text = None
    loop._stream_thinking = None
    loop._accumulated_thinking = ""
    loop._trace_logger = None  # will be lazily set
    loop._tokens_since_last_reminder = 0
    loop._current_objective = ""
    loop._active_constraints = ""
    loop._open_decisions = ""
    return loop


def _make_simple_response(text="done"):
    """Return a NormalizedResponse-like mock with no tool calls."""
    resp = MagicMock()
    resp.text = text
    resp.tool_calls = []
    resp.assistant_content_blocks = []
    resp.input_tokens = 10
    resp.output_tokens = 5
    resp.cached_tokens = 2
    return resp


# ---------------------------------------------------------------------------
# T-15 — learnings suffix in system prompt
# ---------------------------------------------------------------------------

class TestLearningSuffixInjection:
    """T-15: build_learnings_suffix result is injected into the system prompt dynamic part."""

    def test_system_prompt_contains_learnings_suffix(self, tmp_path):
        """initialize(initial_task=...) must call build_learnings_suffix and append the
        result to self._system_prompt.dynamic, AFTER the '## Session' block."""
        from aede.agent import STABLE_SYSTEM_PROMPT

        loop = _make_loop(tmp_path)

        known_suffix = "## Lessons from Prior Runs\n- foo bar\n"

        with patch(
            "aede.memory.injection.build_learnings_suffix",
            return_value=known_suffix,
        ):
            loop.initialize(initial_task="do x")

        dynamic = loop._system_prompt.dynamic
        assert known_suffix in dynamic, (
            f"Expected learnings suffix in dynamic prompt, got:\n{dynamic!r}"
        )
        # Must appear AFTER the ## Session block
        session_pos = dynamic.find("## Session")
        suffix_pos = dynamic.find(known_suffix)
        assert session_pos != -1, "## Session block not found in dynamic prompt"
        assert suffix_pos > session_pos, (
            f"Learnings suffix ({suffix_pos}) must come after ## Session ({session_pos})"
        )
        # Stable must be unchanged
        assert loop._system_prompt.stable == STABLE_SYSTEM_PROMPT

    def test_learnings_suffix_failure_does_not_crash_init(self, tmp_path):
        """If build_learnings_suffix raises, initialize must NOT crash — degrade to no suffix."""
        loop = _make_loop(tmp_path)

        with patch(
            "aede.memory.injection.build_learnings_suffix",
            side_effect=RuntimeError("ollama down"),
        ):
            loop.initialize(initial_task="do x")  # must not raise

        # System prompt must still be built
        assert loop._system_prompt is not None
        assert "## Session" in loop._system_prompt.dynamic

    def test_no_initial_task_skips_suffix(self, tmp_path):
        """When initial_task is None, build_learnings_suffix must NOT be called."""
        loop = _make_loop(tmp_path)

        with patch(
            "aede.memory.injection.build_learnings_suffix",
        ) as mock_suffix:
            loop.initialize()

        mock_suffix.assert_not_called()

    def test_empty_suffix_not_appended(self, tmp_path):
        """If build_learnings_suffix returns empty string, nothing extra in dynamic."""
        loop = _make_loop(tmp_path)

        with patch(
            "aede.memory.injection.build_learnings_suffix",
            return_value="",
        ):
            loop.initialize(initial_task="do x")

        # Should not have the header in dynamic since suffix is empty
        assert "## Lessons from Prior Runs" not in loop._system_prompt.dynamic

    def test_stable_unchanged_when_suffix_present(self, tmp_path):
        """STABLE_SYSTEM_PROMPT constant must not be modified by T-15 wiring."""
        from aede.agent import STABLE_SYSTEM_PROMPT

        loop = _make_loop(tmp_path)
        with patch(
            "aede.memory.injection.build_learnings_suffix",
            return_value="## Lessons from Prior Runs\n- baz\n",
        ):
            loop.initialize(initial_task="task")

        assert loop._system_prompt.stable == STABLE_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# T-13x — per-turn GEPA trace write
# ---------------------------------------------------------------------------

class TestPerTurnTraceWrite:
    """T-13x: after each run_turn completes, a trace record must be written."""

    @pytest.mark.asyncio
    async def test_trace_written_per_turn(self, tmp_path):
        """run_turn must write one JSONL trace record at data_dir/traces/<session_id>.jsonl."""
        loop = _make_loop(tmp_path)
        loop._system_prompt = MagicMock()

        resp = _make_simple_response()

        async def fake_stream(*a, **kw):
            return resp

        loop._stream_response = fake_stream

        async def no_compact():
            pass
        loop._maybe_compact = no_compact

        await loop.run_turn("hello")

        traces_dir = tmp_path / "data" / "traces"
        trace_file = traces_dir / "test-session-001.jsonl"
        assert trace_file.exists(), f"Expected trace file at {trace_file}"

        lines = trace_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1, f"Expected 1 trace line, got {len(lines)}"

        record = json.loads(lines[0])
        assert record["turn_number"] == 1
        assert record["input_tokens"] == 10
        assert record["output_tokens"] == 5
        assert record["outcome"] == "completed"
        assert record["schema_version"] == "phase2-draft"

    @pytest.mark.asyncio
    async def test_trace_accumulates_tokens_across_iterations(self, tmp_path):
        """When the provider is called multiple times in one turn (tool loops),
        tokens must be summed across all iterations."""
        loop = _make_loop(tmp_path)
        loop._system_prompt = MagicMock()

        # First response: has a tool call
        from aede.tools.router import ToolResult
        resp1 = MagicMock()
        resp1.text = ""
        resp1.tool_calls = [{"id": "tc1", "name": "read_file", "input": {"path": "/x"}}]
        resp1.assistant_content_blocks = []
        resp1.input_tokens = 20
        resp1.output_tokens = 10
        resp1.cached_tokens = 3

        # Second response: done
        resp2 = _make_simple_response("done")
        resp2.input_tokens = 30
        resp2.output_tokens = 8
        resp2.cached_tokens = 1

        call_n = {"n": 0}

        async def fake_stream(*a, **kw):
            call_n["n"] += 1
            return resp1 if call_n["n"] == 1 else resp2

        loop._stream_response = fake_stream
        loop._router.execute_sync = MagicMock(
            return_value=ToolResult(status="success", output="content", duration_ms=5)
        )

        async def no_compact():
            pass
        loop._maybe_compact = no_compact

        await loop.run_turn("read something")

        trace_file = tmp_path / "data" / "traces" / "test-session-001.jsonl"
        assert trace_file.exists()
        record = json.loads(trace_file.read_text(encoding="utf-8").splitlines()[0])

        # Tokens must be summed: 20+30=50 input, 10+8=18 output
        assert record["input_tokens"] == 50
        assert record["output_tokens"] == 18

    @pytest.mark.asyncio
    async def test_trace_failure_does_not_crash_turn(self, tmp_path):
        """A failure in trace writing must not propagate — turn completes normally."""
        loop = _make_loop(tmp_path)
        loop._system_prompt = MagicMock()

        resp = _make_simple_response()

        async def fake_stream(*a, **kw):
            return resp

        loop._stream_response = fake_stream

        async def no_compact():
            pass
        loop._maybe_compact = no_compact

        # Patch TraceLogger.write_turn_trace to raise
        with patch(
            "aede.trace.logger.TraceLogger.write_turn_trace",
            side_effect=OSError("disk full"),
        ):
            # Should NOT raise
            await loop.run_turn("hello")

    @pytest.mark.asyncio
    async def test_two_turns_write_two_lines(self, tmp_path):
        """Two calls to run_turn must produce two lines in the same JSONL file."""
        loop = _make_loop(tmp_path)
        loop._system_prompt = MagicMock()

        async def fake_stream(*a, **kw):
            return _make_simple_response()

        loop._stream_response = fake_stream

        async def no_compact():
            pass
        loop._maybe_compact = no_compact

        await loop.run_turn("turn one")
        await loop.run_turn("turn two")

        trace_file = tmp_path / "data" / "traces" / "test-session-001.jsonl"
        lines = trace_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

        r1, r2 = json.loads(lines[0]), json.loads(lines[1])
        assert r1["turn_number"] == 1
        assert r2["turn_number"] == 2
