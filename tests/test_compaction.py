import pytest
from jarvis.compaction import collapse_old_tool_outputs, count_tokens_approx, needs_compaction


def test_count_tokens_approx():
    assert count_tokens_approx("hello world") == pytest.approx(2, abs=2)
    assert count_tokens_approx("a" * 400) == pytest.approx(100, abs=5)


def test_needs_compaction_below_threshold():
    assert needs_compaction(current_tokens=1000, context_window=200000, threshold=0.85) is False


def test_needs_compaction_above_threshold():
    assert needs_compaction(current_tokens=180000, context_window=200000, threshold=0.85) is True


def test_needs_compaction_at_exact_threshold():
    assert needs_compaction(current_tokens=170000, context_window=200000, threshold=0.85) is True


def test_collapse_old_tool_outputs_replaces_old():
    messages = []
    for i in range(15):
        messages.append({
            "role": "tool_result",
            "content": "x" * 500,
            "turn": i,
        })
    collapsed, tokens_saved = collapse_old_tool_outputs(messages, keep_last_n_turns=10)
    old_msgs = [m for m in collapsed if m["turn"] < 5]
    for m in old_msgs:
        assert "[" in m["content"]
        assert "compacted" in m["content"]
    assert tokens_saved > 0


def test_collapse_old_tool_outputs_preserves_recent():
    messages = []
    for i in range(15):
        messages.append({
            "role": "tool_result",
            "content": "important output",
            "turn": i,
        })
    collapsed, _ = collapse_old_tool_outputs(messages, keep_last_n_turns=10)
    recent = [m for m in collapsed if m["turn"] >= 5]
    for m in recent:
        assert m["content"] == "important output"


def test_collapse_skips_non_tool_messages():
    messages = [
        {"role": "user", "content": "hello " * 200, "turn": 0},
        {"role": "assistant", "content": "response " * 200, "turn": 0},
    ]
    collapsed, tokens_saved = collapse_old_tool_outputs(messages, keep_last_n_turns=10)
    assert tokens_saved == 0
    assert collapsed[0]["content"] == messages[0]["content"]
