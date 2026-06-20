"""Tests for the behavior contract in STABLE_SYSTEM_PROMPT."""

import pathlib


FIXTURE = pathlib.Path("tests/fixtures/system_prompt_baseline/stable_prompt.txt")
SECTIONS = pathlib.Path("tests/fixtures/system_prompt_baseline/behavior_contract_sections.txt")


def _prompt() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _sections() -> list[str]:
    raw = SECTIONS.read_text(encoding="utf-8").strip()
    return [s.strip() for s in raw.split("\n") if s.strip()]


def test_prompt_is_not_empty():
    assert len(_prompt()) > 100


def test_all_behavior_contract_sections_present():
    prompt = _prompt()
    for section in _sections():
        assert section in prompt, f"Missing section: {section}"


def test_authority_level_tags_present():
    prompt = _prompt()
    assert "[CONTRACT: absolute]" in prompt
    assert "[CONTRACT: default]" in prompt
    assert "[CONTRACT: style]" in prompt


def test_instruction_hierarchy_present():
    prompt = _prompt()
    assert "instruction hierarchy" in prompt.lower() or "authority" in prompt.lower()


def test_tool_discipline_bidirectional():
    prompt = _prompt()
    assert "use" in prompt.lower()
    assert "NOT" in prompt or "not" in prompt


def test_act_vs_ask_threshold_present():
    prompt = _prompt()
    assert "act" in prompt.lower()
    assert "plan" in prompt.lower()


def test_confirmation_policy_present():
    prompt = _prompt()
    assert "approval" in prompt.lower() or "confirmation" in prompt.lower()


def test_tool_output_authority_present():
    prompt = _prompt()
    assert "tool output" in prompt.lower() or "information" in prompt.lower()


def test_binding_switch_clause_present():
    prompt = _prompt()
    assert '"Use X instead of Y" is a binding switch' in prompt


def test_unavailable_tool_clause_present():
    prompt = _prompt()
    assert "report that it is unavailable" in prompt
    assert "do NOT substitute" in prompt
