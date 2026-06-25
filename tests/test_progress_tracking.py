"""Tests for progress tracking tool."""

from pathlib import Path

SID_A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
SID_B = "01ARZ3NDEKTSV4RRFFQ69G5FAW"


def test_write_progress_appends_to_file(tmp_path: Path):
    from aede.tools.plan_mode import write_progress

    result1 = write_progress({"content": "Step 1 done"}, project_dir=tmp_path, session_id=SID_A)
    result2 = write_progress({"content": "Step 2 done"}, project_dir=tmp_path, session_id=SID_A)

    progress_file = tmp_path / "docs-internal" / "plans" / f"{SID_A}-progress.md"
    assert progress_file.exists()

    text = progress_file.read_text()
    assert "Step 1 done" in text
    assert "Step 2 done" in text
    assert "Progress updated" in result1


def test_write_progress_empty_content(tmp_path: Path):
    from aede.tools.plan_mode import write_progress

    result = write_progress({"content": ""}, project_dir=tmp_path, session_id=SID_B)
    assert "nothing written" in result.lower()


def test_write_progress_tool_registered():
    import pathlib
    source = pathlib.Path("aede/tools/router.py").read_text(encoding="utf-8")
    assert "write_progress" in source


def test_write_progress_in_read_tools():
    import pathlib
    source = pathlib.Path("aede/gate.py").read_text(encoding="utf-8")
    assert '"write_progress"' in source


def test_reinjection_mentions_plan_reread():
    """_inject_reminder must tell the agent to re-read the plan."""
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text(encoding="utf-8")
    assert "read_plan_artifact" in source.lower()
