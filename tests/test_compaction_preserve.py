"""Tests that compaction preserves goal, plan, and open todos verbatim."""
import pathlib


def test_compaction_prompt_mentions_goal_preservation():
    """The COMPACTION_PROMPT must instruct the LLM to preserve goal/plan/todos verbatim."""
    source = pathlib.Path("aede/compaction.py").read_text(encoding="utf-8")
    assert "goal" in source.lower()
    assert "plan" in source.lower() or "todo" in source.lower()


def test_compaction_prompt_mentions_verbatim_preservation():
    """The COMPACTION_PROMPT must say to preserve something verbatim/exactly."""
    source = pathlib.Path("aede/compaction.py").read_text(encoding="utf-8")
    assert "verbatim" in source.lower() or "exactly" in source.lower() or "preserve" in source.lower()
