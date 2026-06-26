"""End-to-end integration tests for plan mode lifecycle.

These tests verify that all plan-mode pieces are wired together correctly
without requiring a live LLM backend.
"""
import pathlib
import tempfile
from pathlib import Path


def test_plan_mode_reminder_active_in_plan_mode():
    """build_system_prompt must include plan-mode reminder when gate_mode is plan."""
    from aede.agent import build_system_prompt

    class Cfg:
        model = "claude-sonnet-4-20250514"
        shell = "powershell"
        tool_output_max_tokens = 8000
        context_window = 200000
        compaction_threshold = 0.85
        gate_mode = "plan"
        home = Path("/tmp")
        grounding_enabled = False

    cfg = Cfg()
    result = build_system_prompt(
        cfg, session_id="test", is_resume=False,
        session_notes=None, compaction_summary=None,
    )

    assert "plan mode" in result.dynamic.lower()
    assert "read-only" in result.dynamic.lower()
    assert "MUST NOT" in result.dynamic


def test_plan_mode_reminder_inactive_in_normal_mode():
    """build_system_prompt must NOT include plan-mode reminder in normal mode."""
    from aede.agent import build_system_prompt

    class Cfg:
        model = "claude-sonnet-4-20250514"
        shell = "powershell"
        tool_output_max_tokens = 8000
        context_window = 200000
        compaction_threshold = 0.85
        gate_mode = "normal"
        home = Path("/tmp")
        grounding_enabled = False

    cfg = Cfg()
    result = build_system_prompt(
        cfg, session_id="test", is_resume=False,
        session_notes=None, compaction_summary=None,
    )

    assert "read-only" not in result.dynamic.lower()


def test_plan_mode_read_only_tools_defined():
    """READ_TOOLS must contain plan artifact tools and exclude write tools."""
    from aede.gate import READ_TOOLS, WRITE_TOOLS

    assert "read_plan_artifact" in READ_TOOLS
    assert "write_plan_artifact" in READ_TOOLS
    assert "write_progress" in READ_TOOLS

    # Plan artifact tools should be readable (auto-allowed in plan mode)
    assert "write_file" not in READ_TOOLS
    assert "write_file" in WRITE_TOOLS


def test_plan_artifact_tools_available():
    """Both plan artifact tools must be registered in the router schemas."""
    from aede.tools.router import _TOOL_SCHEMAS

    assert "write_plan_artifact" in _TOOL_SCHEMAS
    assert "read_plan_artifact" in _TOOL_SCHEMAS

    schema = _TOOL_SCHEMAS["write_plan_artifact"]
    assert "content" in schema["input_schema"]["required"]


def test_plan_artifact_round_trip(tmp_path: Path):
    """Write a plan, read it back, verify content survived."""
    from aede.tools.plan_mode import write_plan_artifact, read_plan_artifact

    sid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    content = "# My Plan\n\n1. Research\n2. Implement\n3. Test"

    write_plan_artifact({"content": content}, project_dir=tmp_path, session_id=sid)
    result = read_plan_artifact({}, project_dir=tmp_path, session_id=sid)

    assert result == content


def test_plan_file_references_wired():
    """system prompt building must reference plan files when they exist."""
    import tempfile
    from pathlib import Path
    from aede.agent import build_system_prompt

    tmp = Path(tempfile.mkdtemp())
    plans_dir = tmp / "docs-internal" / "plans"
    plans_dir.mkdir(parents=True)
    sid = "e2e-ref-test"
    (plans_dir / f"{sid}.md").write_text("# Plan")

    class Cfg:
        model = "claude-sonnet-4-20250514"
        shell = "powershell"
        tool_output_max_tokens = 8000
        context_window = 200000
        compaction_threshold = 0.85
        gate_mode = "normal"
        home = Path("/tmp")
        project_dir = str(tmp)
        grounding_enabled = False

    cfg = Cfg()
    result = build_system_prompt(
        cfg, session_id=sid, is_resume=False,
        session_notes=None, compaction_summary=None,
    )

    assert "plan file exists" in result.dynamic.lower()


def test_behavior_contract_present():
    """The behavior contract must be in the stable system prompt."""
    from aede.agent import STABLE_SYSTEM_PROMPT

    assert "Behavior Contract" in STABLE_SYSTEM_PROMPT
    assert "[CONTRACT: absolute]" in STABLE_SYSTEM_PROMPT
    assert "[CONTRACT: default]" in STABLE_SYSTEM_PROMPT
    assert "Act vs Ask" in STABLE_SYSTEM_PROMPT
    assert "Code vs Plan" in STABLE_SYSTEM_PROMPT
