"""
Context compaction for long-running Jarvis sessions.

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
    """
    Full compaction sequence.
    Returns dict with keys: messages, summary, tokens_reclaimed, method
    method: "string_pass_only" | "llm_summary" | "none"
    """
    current_tokens = sum(count_tokens_approx(m.get("content", "")) for m in messages)

    if not needs_compaction(current_tokens, context_window, threshold):
        return {"messages": messages, "summary": None, "tokens_reclaimed": 0, "method": "none"}

    # Step 1: O(n) string pass
    collapsed, saved = collapse_old_tool_outputs(messages)
    new_tokens = current_tokens - saved

    if not needs_compaction(new_tokens, context_window, threshold):
        return {
            "messages": collapsed,
            "summary": None,
            "tokens_reclaimed": saved,
            "method": "string_pass_only",
        }

    # Step 2: LLM summarization — preserve head (first 3) + tail (last 15)
    head = collapsed[:3]
    tail = collapsed[-15:] if len(collapsed) > 15 else []
    middle = collapsed[3:len(collapsed) - 15] if len(collapsed) > 18 else collapsed[3:]

    middle_text = "\n\n".join(
        f"[{m.get('role', 'unknown')}]: {m.get('content', '')}"
        for m in middle
    )

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

    return {
        "messages": new_messages,
        "summary": summary,
        "tokens_reclaimed": tokens_reclaimed,
        "method": "llm_summary",
        "messages_compacted": len(middle),
    }
