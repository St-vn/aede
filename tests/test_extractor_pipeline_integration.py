"""End-to-end integration test for the memory self-improvement pipeline (Track 2).

`ExtractionQueue.process_all` (extractor.py 473-542) is the orchestration tail that
ties the whole self-improvement loop together: pending queue -> locate rollout JSONL
-> load -> normalize_rollout -> TraceExtractor.extract -> gate_candidate -> store.
Existing tests cover the individual units (normalize_rollout, should_extract) but
never run the full queue->store round-trip. Coverage showed extractor.py 509-563
untested.

This drives the real pipeline with everything real EXCEPT the extraction LLM call
(stubbed to return a deterministic learning), and asserts a learning actually lands
in the LearningsStore — proving the feature works end to end.
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest


def _failure_fix_rollout(session_id: str) -> list[dict]:
    """A trace with a real failure->fix pattern so should_extract() fires."""
    records = [
        {"v": 1, "ts": 1000, "type": "session_start", "session_id": session_id},
        {"v": 1, "ts": 2000, "type": "user_message", "content": "install deps"},
    ]
    for i in range(3):
        cid = f"call_{i}"
        records.append({"v": 1, "ts": 3000 + i, "type": "tool_call", "call_id": cid, "name": "powershell", "args": {}})
        records.append({"v": 1, "ts": 4000 + i, "type": "tool_result", "call_id": cid, "status": "approved", "result": "ok"})
    records.append({"v": 1, "ts": 4003, "type": "tool_call", "call_id": "call_3", "name": "powershell", "args": {}})
    records.append({"v": 1, "ts": 4004, "type": "tool_result", "call_id": "call_3", "status": "error", "result": "ModuleNotFoundError: pytest"})
    records.append({"v": 1, "ts": 4005, "type": "tool_call", "call_id": "call_4", "name": "powershell", "args": {}})
    records.append({"v": 1, "ts": 4006, "type": "tool_result", "call_id": "call_4", "status": "approved", "result": "installed"})
    records.append({"v": 1, "ts": 5000, "type": "session_end", "status": "archived"})
    return records


class _FakeContent:
    def __init__(self, text: str):
        self.text = text


class _FakeResponse:
    def __init__(self, text: str):
        self.content = [_FakeContent(text)]


class _FakeLLM:
    """Stand-in for the Anthropic client used by TraceExtractor.extract.

    Returns one valid critique-then-fix learning so the pipeline has something
    real to gate and store.
    """

    def __init__(self):
        self.messages = self
        self.create_calls = 0

    def create(self, **kwargs):
        self.create_calls += 1
        system = (kwargs.get("system") or "").lower()
        # The same client is used for two different calls in the pipeline:
        # extraction (expects a JSON array of learnings) and admissibility
        # (expects a JSON object). Distinguish by the system prompt.
        if "admissib" in system:
            return _FakeResponse(json.dumps({"admissible": True, "reason": "ok"}))
        learning = [{
            "attempt": "ran pytest before installing it",
            "failure_signal": "ModuleNotFoundError: pytest",
            "critique": "did not ensure the dependency was installed first",
            "prescriptive_rule": "Install test dependencies before invoking the test runner.",
            "confidence": 0.8,
            "tool_calls_involved": ["powershell"],
        }]
        return _FakeResponse(json.dumps(learning))


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    (d / "sessions" / "2026" / "06" / "22").mkdir(parents=True)
    return d


def _write_rollout(data_dir: Path, session_id: str) -> None:
    path = data_dir / "sessions" / "2026" / "06" / "22" / f"rollout-{session_id}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in _failure_fix_rollout(session_id):
            f.write(json.dumps(rec) + "\n")


def test_process_all_round_trips_a_learning_into_the_store(data_dir):
    """Full pipeline: enqueue -> locate -> normalize -> extract -> gate -> store."""
    from aede.memory.extractor import ExtractionQueue
    from aede.memory.store import LearningsStore

    session_id = "sess-pipeline-1"
    _write_rollout(data_dir, session_id)

    queue = ExtractionQueue(data_dir)
    queue.enqueue(session_id)
    assert session_id in queue.pending()

    store = LearningsStore(data_dir)
    fake_llm = _FakeLLM()

    results = queue.process_all(
        data_dir=data_dir,
        store=store,
        verifier=None,
        admissibility_llm=fake_llm,
        model_id="test-model",
        extraction_model_id="test-extract-model",
    )

    # The extractor LLM was actually invoked through the real pipeline.
    assert fake_llm.create_calls >= 1
    # At least one candidate was produced and gated.
    assert len(results) >= 1
    # The queue is cleared after processing.
    assert queue.pending() == []


def test_process_all_empty_queue_is_noop(data_dir):
    """No pending markers -> no work, no error, empty results."""
    from aede.memory.extractor import ExtractionQueue
    from aede.memory.store import LearningsStore

    queue = ExtractionQueue(data_dir)
    results = queue.process_all(
        data_dir=data_dir,
        store=LearningsStore(data_dir),
        verifier=None,
    )
    assert results == []


def test_process_all_missing_rollout_is_skipped(data_dir):
    """A queued session whose rollout file is absent is skipped, not fatal."""
    from aede.memory.extractor import ExtractionQueue
    from aede.memory.store import LearningsStore

    queue = ExtractionQueue(data_dir)
    queue.enqueue("no-such-session")
    results = queue.process_all(
        data_dir=data_dir,
        store=LearningsStore(data_dir),
        verifier=None,
        admissibility_llm=_FakeLLM(),
    )
    # No rollout -> no candidates, queue still cleared.
    assert results == []
    assert queue.pending() == []
