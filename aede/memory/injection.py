"""
Learnings injection for aede system prompt — Phase 2 Memory Phase C.

Provides build_learnings_suffix() which retrieves relevant learnings and
formats them as a markdown block for appending to the system prompt.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aede.db import DB

_CHARS_PER_TOKEN = 4  # consistent with router._truncate estimate
_HEADER = "## Lessons from Prior Runs\n"


def build_learnings_suffix(
    task_description: str,
    db: "DB",
    max_tokens: int = 2000,
) -> str:
    """Build a markdown block of relevant learnings for the system prompt.

    Calls ``hybrid_retrieve`` to find the most relevant trusted learnings for
    *task_description*, formats them under a standard header, and truncates
    from the least-relevant end if the result would exceed *max_tokens*.

    Args:
        task_description: The current task — used as the retrieval query.
        db: DB instance.
        max_tokens: Token budget (estimated at ~4 chars/token).

    Returns:
        A markdown string starting with ``## Lessons from Prior Runs``, or an
        empty string if no relevant learnings are found.
    """
    from aede.memory.retrieval import hybrid_retrieve  # lazy

    results = hybrid_retrieve(task_description, db=db, trusted_only=True)

    if not results:
        return ""

    char_budget = max_tokens * _CHARS_PER_TOKEN
    lines: list[str] = [_HEADER]
    used_chars = len(_HEADER)

    for row in results:
        content: str = row.get("content", "")
        lower_trust: bool = bool(row.get("lower_trust"))

        if lower_trust:
            provenance = "verified by LLM coherence (may be imperfect)"
        else:
            provenance = "verified by test"

        entry = f"- {content} *({provenance})*\n"

        if used_chars + len(entry) > char_budget:
            # Truncate this entry to fit remaining budget
            remaining = char_budget - used_chars
            if remaining > 20:
                entry = entry[: remaining - 3] + "...\n"
                lines.append(entry)
            break

        lines.append(entry)
        used_chars += len(entry)

    result = "".join(lines)
    return result
