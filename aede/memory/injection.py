from __future__ import annotations
from typing import Any


async def build_learnings_suffix(
    store: Any,
    task_description: str,
    max_tokens: int = 2000,
) -> str:
    """Build a markdown suffix of relevant learnings within token budget."""
    from aede.memory.retrieval import hybrid_retrieve

    results = await hybrid_retrieve(store=store, query=task_description, k=10, trusted_only=True)

    if not results:
        return ""

    parts = ["", "## Lessons from Prior Runs", ""]
    budget_chars = max_tokens * 4

    for r in results:
        learning = r["learning"]
        provenance = ""
        if learning.get("verifier_outcome") == "pass":
            provenance = " *(verified by test)*"
        elif learning.get("lower_trust"):
            provenance = " *(verified by LLM coherence)*"

        line = f"- [{learning['type']}] {learning['content']}{provenance}"
        line_chars = len(line) + 1

        current_total = sum(len(p) for p in parts)
        if current_total + line_chars > budget_chars:
            break

        parts.append(line)

    return "\n".join(parts)
