import pytest
from pathlib import Path
from unittest.mock import MagicMock


def test_write_learning_append(tmp_path):
    """write_learning appends a JSONL line with all required fields."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(
        type=LearningType.ANTI_PATTERN,
        content="Avoid using bare except clauses",
        source=LearningSource.USER,
        source_session_id="session-001",
    )

    lines = store._path.read_text().strip().split("\n")
    assert len(lines) == 1

    import json
    data = json.loads(lines[0])
    assert data["type"] == "anti-pattern"
    assert data["content"] == "Avoid using bare except clauses"
    assert data["source"] == "user"
    assert data["source_session_id"] == "session-001"
    assert data["trusted"] is False
    assert "id" in data
    assert "created_at" in data


def test_write_learning_multiple(tmp_path):
    """Multiple writes append sequentially."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ROOT_CAUSE, "First", LearningSource.USER, "s1")
    store.write_learning(LearningType.FAILED_APPROACH, "Second", LearningSource.AUTO_LEARNED, "s2")

    lines = store._path.read_text().strip().split("\n")
    assert len(lines) == 2
    import json
    assert json.loads(lines[0])["content"] == "First"
    assert json.loads(lines[1])["content"] == "Second"


def test_provenance_fields(tmp_path):
    """Written learning contains source, trusted, source_session_id, verifier_outcome."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(
        type=LearningType.CONFIG_CORRECTION,
        content="Set context_window to 200000",
        source=LearningSource.TOOL_ERROR,
        source_session_id="session-002",
    )

    import json
    data = json.loads(store._path.read_text().strip())
    assert data["source"] == "tool_error"
    assert data["trusted"] is False
    assert data["lower_trust"] is False
    assert data["source_session_id"] == "session-002"
    assert data["verifier_outcome"] is None


def test_provenance_type_validation(tmp_path):
    """Invalid type/source raises ValueError."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    with pytest.raises(ValueError, match="type"):
        store.write_learning("bad_type", "content", LearningSource.USER, "s1")


def test_read_all_learnings(tmp_path):
    """Read all returns list of dicts from JSONL."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "First", LearningSource.USER, "s1")
    store.write_learning(LearningType.ROOT_CAUSE, "Second", LearningSource.AUTO_LEARNED, "s2")

    all_items = store.read_all()
    assert len(all_items) == 2
    assert all_items[0]["content"] == "First"


def test_delete_learning(tmp_path):
    """Delete removes by id."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Keep me", LearningSource.USER, "s1")
    store.write_learning(LearningType.ROOT_CAUSE, "Delete me", LearningSource.USER, "s2")

    all_items = store.read_all()
    target_id = all_items[1]["id"]
    store.delete(target_id)

    remaining = store.read_all()
    assert len(remaining) == 1
    assert remaining[0]["content"] == "Keep me"


def test_update_learning(tmp_path):
    """Update replaces content by id."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Old content", LearningSource.USER, "s1")

    all_items = store.read_all()
    target_id = all_items[0]["id"]
    store.update(target_id, content="Updated content")

    updated = store.read_all()
    assert updated[0]["content"] == "Updated content"
