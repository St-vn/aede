import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_memory_list(tmp_path):
    """aede memory list prints learnings in table format."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource
    from aede.commands import handle_learnings_list

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Avoid bare except", LearningSource.USER, "s1")

    console = MagicMock()
    handle_learnings_list(store, console)
    assert console.print.called


def test_memory_show(tmp_path):
    """aede memory show <id> prints single learning detail."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource
    from aede.commands import handle_learnings_show

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Show this", LearningSource.USER, "s1")

    console = MagicMock()
    items = store.read_all()
    handle_learnings_show(items[0]["id"], store, console)
    assert console.print.called


def test_memory_delete(tmp_path):
    """aede memory delete <id> removes learning."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource
    from aede.commands import handle_learnings_delete

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Delete me", LearningSource.USER, "s1")

    items = store.read_all()
    handle_learnings_delete(items[0]["id"], store, MagicMock())

    assert len(store.read_all()) == 0


def test_memory_edit(tmp_path):
    """aede memory edit <id> opens editor and updates content."""
    from aede.memory.store import LearningsStore, LearningType, LearningSource
    from aede.commands import handle_learnings_edit

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Old content", LearningSource.USER, "s1")

    items = store.read_all()
    with patch("subprocess.run") as mock_run, \
         patch.object(Path, "read_text", return_value="New content"):
        handle_learnings_edit(items[0]["id"], store, MagicMock())

    updated = store.read_all()
    assert updated[0]["content"] == "New content"
