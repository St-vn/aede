"""
Tests for aede.memory.extractor — TraceStep, Trace, normalize_rollout, should_extract, TraceExtractor.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import json
import pytest


# ---------------------------------------------------------------------------
# Fixtures: synthetic rollout records
# ---------------------------------------------------------------------------

def clean_rollout(session_id: str = "s1") -> list[dict]:
    """A successful trace with 8 tool calls, no errors."""
    records = [
        {"v": 1, "ts": 1000, "type": "session_start", "session_id": session_id},
        {"v": 1, "ts": 2000, "type": "user_message", "content": "fix the bug"},
    ]
    for i in range(8):
        cid = f"call_{i}"
        records.append({"v": 1, "ts": 3000 + i, "type": "tool_call", "call_id": cid, "name": "read_file", "args": {}})
        records.append({"v": 1, "ts": 4000 + i, "type": "tool_result", "call_id": cid, "status": "approved", "result": f"content_{i}"})
    records.append({"v": 1, "ts": 5000, "type": "session_end", "status": "archived"})
    return records


def failure_fix_rollout() -> list[dict]:
    """A trace with 6 calls: call 3 errors, call 4 retries and succeeds."""
    records = [
        {"v": 1, "ts": 1000, "type": "session_start", "session_id": "s2"},
        {"v": 1, "ts": 2000, "type": "user_message", "content": "install deps"},
    ]
    for i in range(3):
        cid = f"call_{i}"
        records.append({"v": 1, "ts": 3000 + i, "type": "tool_call", "call_id": cid, "name": "powershell", "args": {}})
        records.append({"v": 1, "ts": 4000 + i, "type": "tool_result", "call_id": cid, "status": "approved", "result": "ok"})

    # Call 3: error
    records.append({"v": 1, "ts": 4003, "type": "tool_call", "call_id": "call_3", "name": "powershell", "args": {}})
    records.append({"v": 1, "ts": 4004, "type": "tool_result", "call_id": "call_3", "status": "error", "result": "ModuleNotFoundError: pytest"})

    # Call 4: retry succeeds
    records.append({"v": 1, "ts": 4005, "type": "tool_call", "call_id": "call_4", "name": "powershell", "args": {}})
    records.append({"v": 1, "ts": 4006, "type": "tool_result", "call_id": "call_4", "status": "approved", "result": "installed"})

    # Call 5: success
    records.append({"v": 1, "ts": 4007, "type": "tool_call", "call_id": "call_5", "name": "read_file", "args": {}})
    records.append({"v": 1, "ts": 4008, "type": "tool_result", "call_id": "call_5", "status": "approved", "result": "done"})

    records.append({"v": 1, "ts": 5000, "type": "session_end", "status": "archived"})
    return records


def transient_only_rollout() -> list[dict]:
    """A trace whose only errors are 429 rate limits."""
    records = [
        {"v": 1, "ts": 1000, "type": "session_start", "session_id": "s3"},
        {"v": 1, "ts": 2000, "type": "user_message", "content": "search web"},
    ]
    for i in range(6):
        cid = f"call_{i}"
        records.append({"v": 1, "ts": 3000 + i, "type": "tool_call", "call_id": cid, "name": "web_search", "args": {}})
        status = "error" if i == 3 else "approved"
        result = "429 rate limit exceeded" if i == 3 else "results"
        records.append({"v": 1, "ts": 4000 + i, "type": "tool_result", "call_id": cid, "status": status, "result": result})
    records.append({"v": 1, "ts": 5000, "type": "session_end", "status": "archived"})
    return records


# ---------------------------------------------------------------------------
# Trace / TraceStep dataclasses
# ---------------------------------------------------------------------------

def test_trace_step_fields():
    """TraceStep holds all required fields."""
    from aede.memory.extractor import TraceStep
    step = TraceStep(index=0, tool_name="read_file", inputs={"path": "/x"}, output="ok", status="approved", score=1.0)
    assert step.index == 0
    assert step.tool_name == "read_file"
    assert step.score == 1.0
    assert step.status == "approved"


def test_trace_dataclass():
    """Trace holds session_id, task_description, steps, final_outcome, tool_call_count."""
    from aede.memory.extractor import Trace, TraceStep
    steps = [TraceStep(index=0, tool_name="read_file", inputs={}, output="ok", status="approved", score=1.0)]
    trace = Trace(session_id="s1", task_description="fix bug", steps=steps, final_outcome="success", tool_call_count=1)
    assert trace.session_id == "s1"
    assert trace.task_description == "fix bug"
    assert len(trace.steps) == 1


# ---------------------------------------------------------------------------
# normalize_rollout
# ---------------------------------------------------------------------------

def test_normalize_rollout_clean(tmp_path):
    """A clean rollout with 8 successful calls produces a Trace with 8 steps all score=1.0."""
    from aede.memory.extractor import normalize_rollout
    records = clean_rollout()
    trace = normalize_rollout(records)

    assert trace.session_id == "s1"
    assert "fix the bug" in trace.task_description
    assert trace.tool_call_count == 8
    assert trace.final_outcome == "success"
    assert all(s.score == 1.0 for s in trace.steps)
    assert all(s.status == "approved" for s in trace.steps)


def test_normalize_rollout_failure_fix():
    """A failure→fix loop: the error step scores 0.0, the retry-success scores 0.5."""
    from aede.memory.extractor import normalize_rollout
    records = failure_fix_rollout()
    trace = normalize_rollout(records)

    assert trace.tool_call_count == 6
    assert trace.final_outcome == "success"

    # Steps 0-2: clean
    assert trace.steps[0].score == 1.0
    assert trace.steps[1].score == 1.0
    assert trace.steps[2].score == 1.0
    # Step 3: error
    assert trace.steps[3].score == 0.0
    assert trace.steps[3].status == "error"
    # Step 4: retry-success
    assert trace.steps[4].score == 0.5
    # Step 5: clean
    assert trace.steps[5].score == 1.0


def test_normalize_rollout_empty():
    """Empty records produce an empty trace (no crash)."""
    from aede.memory.extractor import normalize_rollout
    trace = normalize_rollout([])
    assert trace.tool_call_count == 0
    assert trace.steps == []


def test_normalize_rollout_task_from_first_message():
    """The first user_message content becomes the task_description."""
    from aede.memory.extractor import normalize_rollout
    records = [
        {"v": 1, "ts": 1000, "type": "user_message", "content": "  Refactor the parser  "},
        {"v": 1, "ts": 2000, "type": "session_end", "status": "archived"},
    ]
    trace = normalize_rollout(records)
    assert trace.task_description == "Refactor the parser"


def test_normalize_rollout_task_fallback():
    """When no user_message exists, task_description defaults to 'unknown task'."""
    from aede.memory.extractor import normalize_rollout
    trace = normalize_rollout([{"v": 1, "ts": 1000, "type": "session_end", "status": "archived"}])
    assert trace.task_description == "unknown task"


# ---------------------------------------------------------------------------
# should_extract
# ---------------------------------------------------------------------------

def test_should_extract_skips_low_tool_count():
    """Fewer than 5 tool calls → skip."""
    from aede.memory.extractor import Trace, should_extract
    trace = Trace(session_id="s1", task_description="test", tool_call_count=3)
    assert not should_extract(trace)


def test_should_extract_skips_no_failure():
    """8 calls with no errors → skip."""
    from aede.memory.extractor import should_extract, normalize_rollout
    trace = normalize_rollout(clean_rollout())
    assert trace.tool_call_count >= 5
    assert not should_extract(trace)


def test_should_extract_passes_with_failure_fix():
    """Failure→fix loop with ≥5 calls → extract."""
    from aede.memory.extractor import should_extract, normalize_rollout
    trace = normalize_rollout(failure_fix_rollout())
    assert should_extract(trace)


def test_should_extract_force_bypasses_gate():
    """force=True short-circuits all gate checks."""
    from aede.memory.extractor import Trace, should_extract
    trace = Trace(session_id="s1", task_description="test", tool_call_count=0)
    assert should_extract(trace, force=True)


def test_should_extract_skips_transient_only():
    """Transient-only errors (429) do not trigger extraction."""
    from aede.memory.extractor import should_extract, normalize_rollout
    trace = normalize_rollout(transient_only_rollout())
    assert trace.tool_call_count >= 5
    assert not should_extract(trace)


def test_should_extract_skips_failure_without_fix():
    """An error that is never fixed (no later success) → skip."""
    from aede.memory.extractor import Trace, TraceStep, should_extract
    steps = [
        TraceStep(index=0, tool_name="read_file", inputs={}, output="ok", status="approved", score=1.0),
        TraceStep(index=1, tool_name="powershell", inputs={}, output="ModuleNotFound", status="error", score=0.0),
    ]
    trace = Trace(session_id="s1", task_description="test", steps=steps, tool_call_count=2)
    assert not should_extract(trace)


# ---------------------------------------------------------------------------
# Transient detection
# ---------------------------------------------------------------------------

def test_is_transient_matches():
    """Known transient patterns return True."""
    from aede.memory.extractor import _is_transient
    assert _is_transient("429 rate limit exceeded")
    assert _is_transient("500 internal server error")
    assert _is_transient("connection timeout after 30s")
    assert _is_transient("DNS resolution failed")


def test_is_transient_non_match():
    """Non-transient errors return False."""
    from aede.memory.extractor import _is_transient
    assert not _is_transient("ModuleNotFoundError: pytest")
    assert not _is_transient("SyntaxError: invalid syntax")
    assert not _is_transient("Permission denied")


# ---------------------------------------------------------------------------
# TraceExtractor.extract()
# ---------------------------------------------------------------------------

def _mock_llm(response_text: str) -> MagicMock:
    """Return a mock LLM that returns *response_text* as message content."""
    mock = MagicMock()
    mock.content = [MagicMock()]
    mock.content[0].text = response_text
    llm = MagicMock()
    llm.messages.create.return_value = mock
    return llm


def test_extract_produces_critique_then_fix():
    """Given a failure-fix trace, extract returns records with all required fields."""
    from aede.memory.extractor import TraceExtractor, normalize_rollout

    llm = _mock_llm("""[
  {
    "attempt": "Ran pip install without virtualenv",
    "failure_signal": "ModuleNotFoundError: pytest",
    "critique": "Installing system-wide pollutes the global environment",
    "prescriptive_rule": "Always create and use a virtualenv before pip install",
    "confidence": 0.85
  }
]""")
    extractor = TraceExtractor(llm=llm)
    trace = normalize_rollout(failure_fix_rollout())
    learnings = extractor.extract(trace)

    assert len(learnings) == 1
    for l in learnings:
        assert "attempt" in l
        assert "failure_signal" in l
        assert "critique" in l
        assert "prescriptive_rule" in l
        assert "confidence" in l


def test_extract_skips_on_force_false_with_no_failure():
    """Clean trace with force=False → empty list."""
    from aede.memory.extractor import TraceExtractor, normalize_rollout

    extractor = TraceExtractor(llm=_mock_llm("[]"))
    trace = normalize_rollout(clean_rollout())
    assert extractor.extract(trace, force=False) == []


def test_extract_runs_on_force_true():
    """force=True bypasses the gate (extractor may still return empty if LLM finds nothing)."""
    from aede.memory.extractor import TraceExtractor, Trace

    extractor = TraceExtractor(llm=_mock_llm("[]"))
    trace = Trace(session_id="s1", task_description="test", tool_call_count=3)
    result = extractor.extract(trace, force=True)
    # Gate is bypassed; result depends on LLM (we mocked "[]")
    assert isinstance(result, list)


def test_extract_bounded_at_3():
    """Extractor returns at most 3 learning records."""
    from aede.memory.extractor import TraceExtractor, Trace, TraceStep

    many_items = [
        {"attempt": f"a{i}", "failure_signal": f"e{i}", "critique": f"c{i}", "prescriptive_rule": f"p{i}", "confidence": 0.8}
        for i in range(5)
    ]
    llm = _mock_llm(json.dumps(many_items))
    extractor = TraceExtractor(llm=llm)
    trace = Trace(session_id="s1", task_description="test",
                  steps=[TraceStep(i, "t", {}, "ok", "approved", 1.0) for i in range(6)],
                  tool_call_count=6)
    result = extractor.extract(trace, force=True)
    assert len(result) <= 3


def test_extract_handles_empty_llm_response():
    """Empty LLM reply → empty list (no crash)."""
    from aede.memory.extractor import TraceExtractor, Trace

    extractor = TraceExtractor(llm=_mock_llm(""))
    trace = Trace(session_id="s1", task_description="test", tool_call_count=6)
    result = extractor.extract(trace, force=True)
    assert result == []


def test_extract_handles_code_fence_json():
    """LLM response wrapped in markdown code fence is still parsed."""
    from aede.memory.extractor import TraceExtractor, Trace

    llm = _mock_llm("""```json
[{"attempt": "a", "failure_signal": "e", "critique": "c", "prescriptive_rule": "p", "confidence": 0.9}]
```""")
    extractor = TraceExtractor(llm=llm)
    trace = Trace(session_id="s1", task_description="test", tool_call_count=6)
    result = extractor.extract(trace, force=True)
    assert len(result) == 1
    assert result[0]["attempt"] == "a"


# ---------------------------------------------------------------------------
# Gate pipeline
# ---------------------------------------------------------------------------

def _mock_verifier(trusted: bool = True, outcome: str = "llm_coherence_pass") -> MagicMock:
    v = MagicMock()
    v.run_llm_verify.return_value = {"trusted": trusted, "verifier_outcome": outcome}
    return v


def test_gate_rejects_low_confidence():
    """Confidence < 0.6 → rejected."""
    from aede.memory.extractor import gate_candidate

    candidate = {"confidence": 0.4, "prescriptive_rule": "x", "failure_signal": "import error"}
    result = gate_candidate(candidate, [], verifier=MagicMock(), store=MagicMock())
    assert not result.written
    assert "confidence" in result.reason


def test_gate_rejects_transient():
    """Transient failure_signal → rejected."""
    from aede.memory.extractor import gate_candidate

    candidate = {"confidence": 0.9, "failure_signal": "429 rate limit exceeded", "prescriptive_rule": "x"}
    result = gate_candidate(candidate, [], verifier=MagicMock(), store=MagicMock())
    assert not result.written
    assert "transient" in result.reason


def test_gate_passes_and_writes():
    """A clean candidate passes all gates and is written to the store."""
    from aede.memory.extractor import gate_candidate

    store = MagicMock()
    store.write_learning.return_value = {"id": "test_id", "content": "use pathlib"}

    candidate = {
        "confidence": 0.8,
        "prescriptive_rule": "Always use pathlib over os.path",
        "failure_signal": "AttributeError: module 'os' has no attribute 'path'",
        "provenance": {"source_session_id": "s1", "session_tool_call_count": 6},
    }
    result = gate_candidate(candidate, [], verifier=_mock_verifier(trusted=True), store=store,
                            admissibility_llm=MagicMock(), model_id="sonnet-4", extraction_model_id="haiku")
    assert result.written
    assert result.trusted
    assert result.record is not None
    store.write_learning.assert_called_once()


def test_gate_writes_then_verifies():
    """After writing, the verifier runs and updates trusted status."""
    from aede.memory.extractor import gate_candidate

    store = MagicMock()
    store.write_learning.return_value = {"id": "v_test", "content": "use uv"}

    verifier = _mock_verifier(trusted=False, outcome="llm_coherence_fail")
    candidate = {
        "confidence": 0.8,
        "prescriptive_rule": "Use uv not pip",
        "failure_signal": "pip install failed",
        "provenance": {"source_session_id": "s1", "session_tool_call_count": 6},
    }
    result = gate_candidate(candidate, [], verifier=verifier, store=store,
                            admissibility_llm=MagicMock())
    assert result.written
    assert not result.trusted  # verifier said no
    store.update.assert_called_once()  # store was updated with verdict


# ---------------------------------------------------------------------------
# ExtractionQueue
# ---------------------------------------------------------------------------

def test_extraction_queue_enqueue(tmp_path):
    """enqueue appends a marker to the queue file."""
    from aede.memory.extractor import ExtractionQueue
    q = ExtractionQueue(tmp_path)
    q.enqueue("session-abc")
    assert q.pending() == ["session-abc"]


def test_extraction_queue_pending_empty(tmp_path):
    """No queue file → pending() returns empty list."""
    from aede.memory.extractor import ExtractionQueue
    q = ExtractionQueue(tmp_path / "nonexistent")
    assert q.pending() == []


def test_extraction_queue_clear(tmp_path):
    """clear removes the queue file."""
    from aede.memory.extractor import ExtractionQueue
    q = ExtractionQueue(tmp_path)
    q.enqueue("s1")
    q.clear()
    assert q.pending() == []


def test_extraction_queue_multiple(tmp_path):
    """Multiple enqueues produce multiple pending IDs."""
    from aede.memory.extractor import ExtractionQueue
    q = ExtractionQueue(tmp_path)
    q.enqueue("s1")
    q.enqueue("s2")
    q.enqueue("s3")
    assert q.pending() == ["s1", "s2", "s3"]


def test_extraction_queue_process_all_calls_extractor(tmp_path):
    """process_all reads rollout, normalises, extracts, gates (smoke test with mocks)."""
    from aede.memory.extractor import ExtractionQueue
    from unittest.mock import MagicMock

    q = ExtractionQueue(tmp_path)
    q.enqueue("sess-fake")

    store = MagicMock()
    store.list_all.return_value = []
    store.write_learning.return_value = {"id": "lid", "content": "test"}

    verifier = MagicMock()
    verifier.run_llm_verify.return_value = {"trusted": True, "verifier_outcome": "pass"}

    # No actual rollout file exists → process_all should handle gracefully
    results = q.process_all(
        data_dir=tmp_path,
        store=store,
        verifier=verifier,
        admissibility_llm=MagicMock(),
    )
    assert isinstance(results, list)
    # Process_all may return empty because rollout file doesn't exist — that's OK
    # The test here is that it doesn't crash
    q.clear()
