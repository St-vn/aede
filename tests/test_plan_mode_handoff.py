"""Tests for plan-mode exit + approval handoff (TASK-005)."""

import pathlib
from pathlib import Path


def test_plan_file_reference_in_dynamic_prompt(tmp_path: Path):
    """When a plan file exists and mode is not plan, the prompt should reference it."""
    from aede.agent import build_system_prompt

    plans_dir = tmp_path / "docs-internal" / "plans"
    plans_dir.mkdir(parents=True)
    sid = "test-handoff-session"
    plan_file = plans_dir / f"{sid}.md"
    plan_file.write_text("# Test Plan", encoding="utf-8")

    class MockCfg:
        model = "claude-sonnet-4-20250514"
        shell = "powershell"
        tool_output_max_tokens = 8000
        context_window = 200000
        compaction_threshold = 0.85
        gate_mode = "normal"
        project_dir = tmp_path
        home = Path("/tmp")
        grounding_enabled = False

    cfg = MockCfg()
    result = build_system_prompt(
        cfg, session_id=sid, is_resume=False,
        session_notes=None, compaction_summary=None,
    )

    assert "plan file exists" in result.dynamic.lower()


def test_plan_file_reference_not_injected_in_plan_mode(tmp_path: Path):
    """When gate_mode is plan, the plan file reference should NOT be injected."""
    from aede.agent import build_system_prompt

    plans_dir = tmp_path / "docs-internal" / "plans"
    plans_dir.mkdir(parents=True)
    sid = "test-plan-mode-active"
    plan_file = plans_dir / f"{sid}.md"
    plan_file.write_text("# Test Plan", encoding="utf-8")

    class MockCfg:
        model = "claude-sonnet-4-20250514"
        shell = "powershell"
        tool_output_max_tokens = 8000
        context_window = 200000
        compaction_threshold = 0.85
        gate_mode = "plan"
        project_dir = tmp_path
        home = Path("/tmp")
        grounding_enabled = False

    cfg = MockCfg()
    result = build_system_prompt(
        cfg, session_id=sid, is_resume=False,
        session_notes=None, compaction_summary=None,
    )

    assert "plan file exists" not in result.dynamic.lower()


def test_plan_file_reference_no_file_no_injection(tmp_path: Path):
    """When no plan file exists, no reference should appear."""
    from aede.agent import build_system_prompt

    sid = "test-no-plan-file"

    class MockCfg:
        model = "claude-sonnet-4-20250514"
        shell = "powershell"
        tool_output_max_tokens = 8000
        context_window = 200000
        compaction_threshold = 0.85
        gate_mode = "normal"
        project_dir = tmp_path
        home = Path("/tmp")
        grounding_enabled = False

    cfg = MockCfg()
    result = build_system_prompt(
        cfg, session_id=sid, is_resume=False,
        session_notes=None, compaction_summary=None,
    )

    assert "plan file exists" not in result.dynamic.lower()


def test_plan_mode_reminder_not_in_normal_mode():
    """When gate_mode is normal, plan-mode reminder should NOT be in prompt."""
    source = pathlib.Path("aede/agent.py").read_text(encoding="utf-8")
    assert "plan mode" in source.lower()
    assert "gate_mode" in source.lower()


def test_act_command_is_parsed_as_mode_normal():
    """/act should be parsed as /mode normal."""
    from aede.commands import parse_command

    cmd = parse_command("/act")
    assert cmd is not None
    assert cmd.name == "mode"
    assert cmd.args == ["normal"]


def test_act_command_in_commands_set():
    """/act should be in the COMMANDS set for help text."""
    from aede.commands import COMMANDS
    assert "act" in COMMANDS
