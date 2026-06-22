"""Tests for plan artifact tools (write_plan_artifact, read_plan_artifact)."""

import pathlib
from pathlib import Path


def test_write_plan_artifact_creates_file(tmp_path: Path):
    """write_plan_artifact must create the plan file at the expected path."""
    from aede.tools.plan_mode import write_plan_artifact

    sid = "test-session-001"
    content = "# Test Plan\n\n- Step 1\n- Step 2"

    result = write_plan_artifact(
        {"content": content},
        project_dir=tmp_path,
        session_id=sid,
    )

    expected_path = tmp_path / "docs-internal" / "plans" / f"{sid}.md"
    assert expected_path.exists(), f"Plan file not created at {expected_path}"
    assert "Plan artifact written" in result
    assert expected_path.read_text() == content


def test_write_plan_artifact_empty_content(tmp_path: Path):
    """write_plan_artifact must return an error message for empty content."""
    from aede.tools.plan_mode import write_plan_artifact

    result = write_plan_artifact(
        {"content": ""},
        project_dir=tmp_path,
        session_id="test-session-002",
    )

    assert "nothing written" in result.lower()


def test_read_plan_artifact_returns_content(tmp_path: Path):
    """read_plan_artifact must return the plan file content."""
    from aede.tools.plan_mode import write_plan_artifact, read_plan_artifact

    sid = "test-session-003"
    content = "# Plan\nDo X then Y"

    write_plan_artifact({"content": content}, project_dir=tmp_path, session_id=sid)

    result = read_plan_artifact({}, project_dir=tmp_path, session_id=sid)
    assert result == content


def test_read_plan_artifact_missing_file(tmp_path: Path):
    """read_plan_artifact must return a message for missing plan files."""
    from aede.tools.plan_mode import read_plan_artifact

    result = read_plan_artifact({}, project_dir=tmp_path, session_id="nonexistent")
    assert "no plan found" in result.lower()


def test_plan_artifact_tools_registered():
    """Both plan artifact tools must be registered in the ToolRouter."""
    source = pathlib.Path("aede/tools/router.py").read_text(encoding="utf-8")
    assert "write_plan_artifact" in source
    assert "read_plan_artifact" in source


def test_plan_artifact_tools_in_read_tools():
    """Both plan artifact tools must be in the READ_TOOLS set."""
    source = pathlib.Path("aede/gate.py").read_text(encoding="utf-8")
    assert '"read_plan_artifact"' in source
    assert '"write_plan_artifact"' in source
