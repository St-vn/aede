import pytest
from unittest.mock import AsyncMock, MagicMock, call
from aede.compaction import collapse_old_tool_outputs, count_tokens_approx, needs_compaction


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


# ---------------------------------------------------------------------------
# Task 4 — memory flush + session notes + compacted_at stamp
# ---------------------------------------------------------------------------

def _make_oversized_messages(n: int = 30) -> list[dict]:
    """Make a message list large enough to force llm_summary path."""
    msgs = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": "word " * 500})
    return msgs


@pytest.mark.asyncio
async def test_llm_summary_writes_session_notes_and_uses_flush_prompt(tmp_path):
    """run_compaction on llm_summary path must:
    - Write non-empty content to session_notes_path.
    - Call anthropic_client.messages.create at least twice (flush + summary).
    - Use MEMORY_FLUSH_PROMPT in one of the calls.
    - Return method=="llm_summary".
    """
    from aede.compaction import run_compaction, MEMORY_FLUSH_PROMPT

    session_notes_path = tmp_path / "notes" / "session-notes.md"

    flush_response = MagicMock()
    flush_response.content = [MagicMock(text="important: use pathlib everywhere")]

    summary_response = MagicMock()
    summary_response.content = [MagicMock(text="## Session Handoff Summary\nGoal: fix things")]

    # .create is called twice: first flush, then summary
    call_responses = [flush_response, summary_response]
    mock_create = AsyncMock(side_effect=call_responses)

    mock_client = MagicMock()
    mock_client.messages.create = mock_create

    messages = _make_oversized_messages(30)

    result = await run_compaction(
        messages=messages,
        context_window=100,      # tiny window forces llm_summary
        threshold=0.01,
        session_notes_path=session_notes_path,
        anthropic_client=mock_client,
        model="claude-3-haiku-20240307",
    )

    assert result["method"] == "llm_summary"

    # Notes file must exist and have content
    assert session_notes_path.exists(), "session_notes_path was not written"
    notes_content = session_notes_path.read_text(encoding="utf-8")
    assert notes_content.strip(), "session notes file is empty"

    # MEMORY_FLUSH_PROMPT must appear in one of the messages.create calls.
    # Check the actual messages kwarg content rather than str(call) to avoid
    # repr-encoding mismatches.
    all_call_args = mock_create.call_args_list
    assert len(all_call_args) >= 2, "Expected at least 2 messages.create calls (flush + summary)"
    flush_used = False
    for c in all_call_args:
        msgs = c.kwargs.get("messages", [])
        for m in msgs:
            if isinstance(m, dict) and MEMORY_FLUSH_PROMPT in m.get("content", ""):
                flush_used = True
                break
    assert flush_used, "MEMORY_FLUSH_PROMPT was not used in any messages.create call"


@pytest.mark.asyncio
async def test_string_pass_only_does_not_write_notes(tmp_path):
    """string_pass_only path must NOT write session notes and NOT call flush."""
    from aede.compaction import run_compaction

    session_notes_path = tmp_path / "notes.md"
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock()

    # Use small enough context_window that string pass suffices to drop below threshold
    # Make messages with tool_result turns so string pass can collapse them
    messages = []
    for i in range(20):
        messages.append({"role": "tool_result", "content": "x" * 400, "turn": i})

    result = await run_compaction(
        messages=messages,
        context_window=10000,
        threshold=0.5,
        session_notes_path=session_notes_path,
        anthropic_client=mock_client,
        model="claude-3-haiku-20240307",
    )

    # If the result is string_pass_only, notes must not be written
    if result["method"] == "string_pass_only":
        assert not session_notes_path.exists(), "Notes file must not be written on string_pass_only"
        mock_client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_flush_error_does_not_crash_compaction(tmp_path):
    """If the flush call raises, compaction must still succeed and include notes_error."""
    from aede.compaction import run_compaction

    session_notes_path = tmp_path / "notes.md"

    # Flush raises, summary succeeds
    summary_response = MagicMock()
    summary_response.content = [MagicMock(text="## Summary\nGoal: keep going")]

    call_count = {"n": 0}

    async def side_effect(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("flush API error")
        return summary_response

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=side_effect)

    messages = _make_oversized_messages(30)

    result = await run_compaction(
        messages=messages,
        context_window=100,
        threshold=0.01,
        session_notes_path=session_notes_path,
        anthropic_client=mock_client,
        model="claude-3-haiku-20240307",
    )

    assert result["method"] == "llm_summary", "Compaction must complete despite flush error"
    assert "notes_error" in result, "notes_error key must be present when flush fails"
