"""
Tests for aede.memory.admissibility — rule admissibility check (Meta-Policy Reflexion).
"""
from __future__ import annotations

from unittest.mock import MagicMock
import json
import pytest


def _mock_llm(response_text: str) -> MagicMock:
    """Return a mock LLM client that returns *response_text* as the message content."""
    mock = MagicMock()
    mock.content = [MagicMock()]
    mock.content[0].text = response_text
    llm = MagicMock()
    llm.messages.create.return_value = mock
    return llm


# ---------------------------------------------------------------------------
# check_admissibility
# ---------------------------------------------------------------------------

def test_admissibility_passes_non_conflicting():
    """A rule that does not contradict any existing trusted rule → admissible."""
    from aede.memory.admissibility import check_admissibility

    llm = _mock_llm(json.dumps({"admissible": True, "conflicting_ids": [], "reason": "No conflict."}))
    candidate = {"prescriptive_rule": "Run pytest before committing"}
    existing = [
        {"id": "r1", "content": "Use pathlib for all paths", "trusted": True},
    ]
    result = check_admissibility(candidate, existing, llm=llm)
    assert result.admissible
    assert result.conflicting_rule_ids == []


def test_admissibility_rejects_contradictory():
    """A rule that contradicts an existing trusted rule → inadmissible with conflicting ids."""
    from aede.memory.admissibility import check_admissibility

    llm = _mock_llm(json.dumps({
        "admissible": False,
        "conflicting_ids": ["r_abc"],
        "reason": "New rule says never use write_file but existing rule says always use write_file for edits.",
    }))
    candidate = {"prescriptive_rule": "Never use write_file; always use create_file"}
    existing = [
        {"id": "r_abc", "content": "Always use write_file for edits", "trusted": True},
    ]
    result = check_admissibility(candidate, existing, llm=llm)
    assert not result.admissible
    assert "r_abc" in result.conflicting_rule_ids


def test_admissibility_no_existing_rules():
    """When no existing trusted rules exist, new rule is always admissible."""
    from aede.memory.admissibility import check_admissibility

    llm = _mock_llm(json.dumps({"admissible": True, "conflicting_ids": [], "reason": "No existing rules to conflict with."}))
    candidate = {"prescriptive_rule": "Always use pathlib"}
    result = check_admissibility(candidate, [], llm=llm)
    assert result.admissible


def test_admissibility_empty_rule():
    """A candidate with no prescriptive_rule is trivially admissible."""
    from aede.memory.admissibility import check_admissibility

    result = check_admissibility({"id": "test"}, [], llm=MagicMock())
    assert result.admissible


def test_admissibility_ignores_untrusted_existing():
    """Only trusted=True existing rules are considered — untrusted rules are ignored."""
    from aede.memory.admissibility import check_admissibility

    llm = _mock_llm(json.dumps({"admissible": True, "conflicting_ids": [], "reason": "No conflict."}))
    candidate = {"prescriptive_rule": "Use write_file"}
    existing = [
        {"id": "r1", "content": "Never use write_file", "trusted": False},
    ]
    result = check_admissibility(candidate, existing, llm=llm)
    # The prompt only includes trusted rules, so the LLM sees "(none)"
    assert result.admissible


def test_admissibility_handles_malformed_llm_response():
    """If the LLM returns non-JSON, the check defaults to admissible (fail-open)."""
    from aede.memory.admissibility import check_admissibility

    llm = _mock_llm("I think the rule is fine.")  # not JSON
    candidate = {"prescriptive_rule": "Use pathlib"}
    result = check_admissibility(candidate, [], llm=llm)
    assert result.admissible  # fail-open
    assert "Could not parse" in result.reason
