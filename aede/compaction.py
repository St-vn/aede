"""
Context compaction for long-running aede sessions.

When conversation history grows close to the model's context window, this
module shrinks it in two passes: a cheap string pass that stubs out old tool
outputs, followed (if still over threshold) by an LLM summarisation pass that
collapses the middle of the conversation into a structured handoff summary.
"""
from __future__ import annotations
from typing import Any


COMPACTION_PROMPT = """\
You are summarizing a session for context compaction. Write a structured handoff summary using exactly this template:

## Session Handoff Summary

**Goal:** [what the user is trying to accomplish]
**Constraints:** [hard limits, things to avoid, environment facts]
**Progress:** [what has been done, what worked, what failed and why]
**Key Decisions:** [choices made and reasoning — not just what, but why]
**Critical Context:** [facts the model must retain: paths, names, values]
**Next Steps:** [what was about to happen when compaction fired]

Be specific and dense. Omit nothing that a future instance of yourself would need to continue seamlessly.
"""

MEMORY_FLUSH_PROMPT = """\
Context compaction is about to fire. Before that happens, write any decisions, discoveries, file paths, or critical context that must survive summarization to session_notes.md. Be specific and dense — this file is your memory across the compaction boundary. Reply with only the content to write to session_notes.md, nothing else.
"""


def count_tokens_approx(text: str) -> int:
    """Estimate token count as ``len(text) // 4``, with a minimum of 1."""
    return max(1, len(text) // 4)


def needs_compaction(current_tokens: int, context_window: int, threshold: float) -> bool:
    """Return True when ``current_tokens`` meets or exceeds ``context_window * threshold``."""
    return current_tokens >= int(context_window * threshold)


def needs_cheap_collapse(current_tokens: int, context_window: int) -> bool:
    """Return True when current_tokens >= 50% of context window.

    Triggers the cheap string-pass (collapse_old_tool_outputs) before
    the full LLM-summary compaction.
    """
    return current_tokens >= int(context_window * 0.5)


def collapse_old_tool_outputs(
    messages: list[dict[str, Any]],
    keep_last_n_turns: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    """Replace old tool-result payloads with a compact placeholder.

    Tool results from turns older than ``(max_turn - keep_last_n_turns)`` are
    replaced by a one-line stub that preserves the original token count.  This
    is an O(n) pass with no LLM call.

    Returns:
        A ``(new_messages, tokens_saved)`` tuple.
    """
    if not messages:
        return messages, 0

    max_turn = max(m.get("turn", 0) for m in messages)
    cutoff_turn = max_turn - keep_last_n_turns
    tokens_saved = 0
    result = []

    for msg in messages:
        if msg.get("role") == "tool_result" and msg.get("turn", 0) <= cutoff_turn:
            token_count = count_tokens_approx(msg["content"])
            tokens_saved += token_count
            new_msg = dict(msg)
            new_msg["content"] = f"[tool output — ~{token_count} tokens — compacted]"
            result.append(new_msg)
        else:
            result.append(msg)

    return result, tokens_saved


async def run_compaction(
    messages: list[dict[str, Any]],
    context_window: int,
    threshold: float,
    session_notes_path: Any,
    anthropic_client: Any,
    model: str,
) -> dict[str, Any]:
    """Full compaction sequence with two-phase split trigger.

    Phase 1 (cheap): collapse_old_tool_outputs at 50% of context window.
    Phase 2 (LLM): summarization at threshold (default 85%).

    Returns dict with keys: messages, summary, tokens_reclaimed, method
    method: "string_pass_only" | "llm_summary" | "none"
    """
    current_tokens = sum(count_tokens_approx(m.get("content", "")) for m in messages)

    # Phase 1: Cheap string pass at 50%
    if not needs_cheap_collapse(current_tokens, context_window):
        return {"messages": messages, "summary": None, "tokens_reclaimed": 0, "method": "none"}

    collapsed, saved = collapse_old_tool_outputs(messages)
    new_tokens = current_tokens - saved

    if not needs_compaction(new_tokens, context_window, threshold):
        return {
            "messages": collapsed,
            "summary": None,
            "tokens_reclaimed": saved,
            "method": "string_pass_only",
        }

    # Phase 2: LLM summarization at threshold
    head = collapsed[:3]
    tail = collapsed[-15:] if len(collapsed) > 15 else []
    middle = collapsed[3:len(collapsed) - 15] if len(collapsed) > 18 else collapsed[3:]

    middle_text = "\n\n".join(
        f"[{m.get('role', 'unknown')}]: {m.get('content', '')}"
        for m in middle
    )

    # Memory flush
    notes_error: str | None = None
    try:
        flush_messages = [
            {"role": "user", "content": f"{MEMORY_FLUSH_PROMPT}\n\n<conversation>\n{middle_text}\n</conversation>"}
        ]
        flush_response = await anthropic_client.messages.create(
            model=model,
            max_tokens=1000,
            messages=flush_messages,
        )
        notes_text = flush_response.content[0].text
        from pathlib import Path
        notes_path = Path(session_notes_path)
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_path.write_text(notes_text, encoding="utf-8")
    except Exception as exc:
        notes_error = str(exc)

    summary_messages = [
        {"role": "user", "content": f"{COMPACTION_PROMPT}\n\n<conversation>\n{middle_text}\n</conversation>"}
    ]

    response = await anthropic_client.messages.create(
        model=model,
        max_tokens=2000,
        messages=summary_messages,
    )
    summary = response.content[0].text

    summary_msg = {
        "role": "assistant",
        "content": summary,
        "is_compaction_summary": True,
        "turn": head[-1].get("turn", 0) if head else 0,
    }

    new_messages = head + [summary_msg] + tail
    new_tokens_after = sum(count_tokens_approx(m.get("content", "")) for m in new_messages)
    tokens_reclaimed = current_tokens - new_tokens_after

    result: dict = {
        "messages": new_messages,
        "summary": summary,
        "tokens_reclaimed": tokens_reclaimed,
        "method": "llm_summary",
        "messages_compacted": len(middle),
    }
    if notes_error is not None:
        result["notes_error"] = notes_error
    return result
