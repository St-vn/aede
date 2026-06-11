"""
Rule admissibility — Meta-Policy Reflexion pattern.

Checks whether a candidate prescriptive rule contradicts any existing trusted
rule before it is written to the store.  Uses an LLM (injectable for tests)
to compare the new rule against the existing set.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdmissibilityResult:
    admissible: bool
    conflicting_rule_ids: list[str] = field(default_factory=list)
    reason: str = ""


_ADMISSIBILITY_SYSTEM_PROMPT = (
    "You are a strict rule-admissibility verifier.  Your job is to compare a "
    "new prescriptive rule against a set of existing trusted rules and determine "
    "whether the new rule contradicts any of them.\n\n"
    "Two rules contradict if:\n"
    "- They recommend opposing actions for the same situation\n"
    "- Following one would violate the other\n"
    "- The new rule would override or invalidate an existing rule\n\n"
    'Reply with a JSON object only.  Example:\n'
    '{"admissible": true, "conflicting_ids": [], "reason": "No conflict found."}\n'
    'or\n'
    '{"admissible": false, "conflicting_ids": ["rule_abc"], "reason": "New rule says never use X but existing rule says always use X."}'
)


def _build_admissibility_prompt(
    candidate_rule: str,
    existing: list[dict[str, Any]],
) -> str:
    """Build the user message for the LLM admissibility check."""
    existing_text = "\n".join(
        f"- [{r.get('id', '?')}] {r.get('content', r.get('prescriptive_rule', ''))}"
        for r in existing
        if r.get("trusted")
    )
    return (
        f"New rule: {candidate_rule}\n\n"
        f"Existing trusted rules:\n{existing_text or '(none)'}\n\n"
        "Is the new rule admissible?"
    )


def check_admissibility(
    candidate: dict[str, Any],
    existing: list[dict[str, Any]],
    llm: Any | None = None,
) -> AdmissibilityResult:
    """Check whether *candidate*'s prescriptive_rule contradicts existing rules.

    Args:
        candidate: A dict with at least ``prescriptive_rule`` and optionally
            ``id``.
        existing: List of existing learning records.  Only those with
            ``trusted=True`` are considered.
        llm: An injectable LLM client with a ``messages.create(...)`` method.
            When ``None``, a real ``anthropic.Anthropic`` client is constructed
            lazily (requires ``ANTHROPIC_API_KEY``).  When a mock is provided,
            its return value must have ``.content[0].text`` as a JSON string.

    Returns:
        ``AdmissibilityResult`` with admissible flag, conflicting ids, and
        a human-readable reason.
    """
    rule = candidate.get("prescriptive_rule", candidate.get("content", ""))
    if not rule:
        return AdmissibilityResult(admissible=True, reason="No rule to check.")

    prompt = _build_admissibility_prompt(rule, existing)

    if llm is None:
        import anthropic
        client = anthropic.Anthropic()
    else:
        client = llm

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=_ADMISSIBILITY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    reply_text: str = response.content[0].text if response.content else ""
    try:
        result = json.loads(reply_text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return AdmissibilityResult(
            admissible=True,
            reason=f"Could not parse LLM response: {reply_text[:200]}",
        )

    return AdmissibilityResult(
        admissible=bool(result.get("admissible", True)),
        conflicting_rule_ids=result.get("conflicting_ids", []),
        reason=result.get("reason", ""),
    )
