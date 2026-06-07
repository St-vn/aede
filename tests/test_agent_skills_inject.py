import pytest
from pathlib import Path
from unittest.mock import MagicMock


def test_skills_in_suffix():
    """Skills appended after Session section, STABLE_SYSTEM_PROMPT untouched."""
    from aede.agent import build_system_prompt, STABLE_SYSTEM_PROMPT
    from aede.skills.schema import SkillDef

    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.tool_output_max_tokens = 2000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.8

    skills = [
        SkillDef(name="web_search", description="Search the web", body="## Web Search\nUse this skill."),
        SkillDef(name="data_analysis", description="Analyze data and produce insights", body="## Data Analysis\nCrunch numbers."),
    ]

    prompt = build_system_prompt(
        cfg=cfg,
        session_id="SID001",
        is_resume=False,
        session_notes=None,
        compaction_summary=None,
        skills=skills,
    )

    assert prompt.stable == STABLE_SYSTEM_PROMPT
    assert "## Agent Skills" in prompt.dynamic
    assert "web_search" in prompt.dynamic
    assert "Search the web" in prompt.dynamic
    assert "data_analysis" in prompt.dynamic
    assert "Analyze data" in prompt.dynamic
    assert "Session" in prompt.dynamic
    # Skills section comes after Session
    session_pos = prompt.dynamic.index("## Session")
    skills_pos = prompt.dynamic.index("## Agent Skills")
    assert skills_pos > session_pos


def test_skills_in_suffix_no_skills():
    """Without skills, no Agent Skills section appears."""
    from aede.agent import build_system_prompt, STABLE_SYSTEM_PROMPT

    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.tool_output_max_tokens = 2000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.8

    prompt = build_system_prompt(
        cfg=cfg,
        session_id="SID001",
        is_resume=False,
        session_notes=None,
        compaction_summary=None,
    )

    assert prompt.stable == STABLE_SYSTEM_PROMPT
    assert "## Agent Skills" not in prompt.dynamic


def test_skills_in_suffix_empty_list():
    """Empty skills list does not inject Agent Skills section."""
    from aede.agent import build_system_prompt, STABLE_SYSTEM_PROMPT

    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.tool_output_max_tokens = 2000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.8

    prompt = build_system_prompt(
        cfg=cfg,
        session_id="SID001",
        is_resume=False,
        session_notes=None,
        compaction_summary=None,
        skills=[],
    )

    assert prompt.stable == STABLE_SYSTEM_PROMPT
    assert "## Agent Skills" not in prompt.dynamic
