import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_build_learnings_suffix_formats_markdown(tmp_path):
    """build_learnings_suffix produces markdown with ## Lessons from Prior Runs."""
    from aede.memory.injection import build_learnings_suffix
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Avoid bare except", LearningSource.USER, "s1", trusted=True)
    store.write_learning(LearningType.ROOT_CAUSE, "Use pathlib", LearningSource.AUTO_LEARNED, "s2", trusted=True)

    suffix = await build_learnings_suffix(store=store, task_description="bare except", max_tokens=2000)

    assert "## Lessons from Prior Runs" in suffix
    assert "Avoid bare except" in suffix


@pytest.mark.asyncio
async def test_token_cap_respected(tmp_path):
    """build_learnings_suffix truncates when over token budget."""
    from aede.memory.injection import build_learnings_suffix
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    for i in range(20):
        store.write_learning(LearningType.ANTI_PATTERN, f"Long learning content item number {i} " * 20, LearningSource.USER, "s1", trusted=True)

    suffix = await build_learnings_suffix(store=store, task_description="Long learning content", max_tokens=500)

    assert "Lessons from Prior Runs" in suffix
    rough_tokens = len(suffix) // 4
    assert rough_tokens <= 600  # allow some slack
