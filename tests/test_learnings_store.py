"""
Tests for LearningsStore — T-03 (write_learning JSONL) and T-04 (provenance + schema).

TDD: these tests are written FIRST and must fail before implementation.
"""
from __future__ import annotations
import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# T-03: write_learning append path
# ---------------------------------------------------------------------------


def test_write_learning_append(tmp_home):
    """write_learning appends one JSONL line with all required fields."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    data_dir = tmp_home / "data"
    store = LearningsStore(data_dir)

    store.write_learning(
        type="anti-pattern",
        content="Never do X when Y is true.",
        source="user",
        source_session_id="01SESSION000000000000000S1",
    )

    jsonl_path = data_dir / "learnings.jsonl"
    assert jsonl_path.exists(), "learnings.jsonl was not created"

    lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1, f"Expected 1 JSONL line, got {len(lines)}"

    record = json.loads(lines[0])

    # Required fields
    assert "id" in record, "Missing 'id' field"
    assert isinstance(record["id"], str) and len(record["id"]) > 0
    assert "created_at" in record, "Missing 'created_at' field"
    assert isinstance(record["created_at"], int), "'created_at' must be an int (ms epoch)"
    assert "type" in record and record["type"] == "anti-pattern"
    assert "content" in record and record["content"] == "Never do X when Y is true."
    assert "source" in record and record["source"] == "user"
    assert "source_session_id" in record and record["source_session_id"] == "01SESSION000000000000000S1"
    assert "trusted" in record and record["trusted"] is False, "'trusted' must default to False"


def test_write_learning_appends_multiple(tmp_home):
    """Each call to write_learning appends a new line — does not overwrite."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    data_dir = tmp_home / "data"
    store = LearningsStore(data_dir)

    store.write_learning(type="anti-pattern", content="First", source="user", source_session_id="S1")
    store.write_learning(type="failed-approach", content="Second", source="auto_learned", source_session_id="S2")

    jsonl_path = data_dir / "learnings.jsonl"
    lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2, f"Expected 2 JSONL lines, got {len(lines)}"

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["content"] == "First"
    assert second["content"] == "Second"
    assert first["id"] != second["id"], "Two learnings must have distinct IDs"


# ---------------------------------------------------------------------------
# T-04: Provenance tagging + schema validation
# ---------------------------------------------------------------------------


def test_provenance_fields(tmp_home):
    """Written learning contains source, trusted, source_session_id, lower_trust, verifier_outcome."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    data_dir = tmp_home / "data"
    store = LearningsStore(data_dir)

    store.write_learning(
        type="root-cause",
        content="The bug was in the parser.",
        source="test_failure",
        source_session_id="01SESSION000000000000000S2",
    )

    jsonl_path = data_dir / "learnings.jsonl"
    lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    record = json.loads(lines[0])

    # Provenance fields per T-04
    assert record["source"] == "test_failure"
    assert record["trusted"] is False, "'trusted' default is False"
    assert record["lower_trust"] is False, "'lower_trust' default is False"
    assert record["verifier_outcome"] is None, "'verifier_outcome' default is None"
    assert record["source_session_id"] == "01SESSION000000000000000S2"


def test_invalid_type_rejected(tmp_home):
    """write_learning raises ValueError for an invalid 'type'."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")

    with pytest.raises(ValueError, match="type"):
        store.write_learning(
            type="not-a-valid-type",
            content="Some content.",
            source="user",
            source_session_id="S1",
        )


def test_invalid_source_rejected(tmp_home):
    """write_learning raises ValueError for an invalid 'source'."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")

    with pytest.raises(ValueError, match="source"):
        store.write_learning(
            type="anti-pattern",
            content="Some content.",
            source="made_up_source",
            source_session_id="S1",
        )


def test_all_valid_types_accepted(tmp_home):
    """All four valid type values are accepted without error."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")

    valid_types = ["anti-pattern", "failed-approach", "root-cause", "config-correction"]
    for t in valid_types:
        store.write_learning(type=t, content=f"Content for {t}", source="user", source_session_id="S1")


def test_all_valid_sources_accepted(tmp_home):
    """All four valid source values are accepted without error."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")

    valid_sources = ["user", "auto_learned", "test_failure", "tool_error"]
    for s in valid_sources:
        store.write_learning(type="anti-pattern", content=f"Content for {s}", source=s, source_session_id="S1")
