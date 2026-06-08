import pytest
from pathlib import Path


def _write_skill(dir: Path, name: str, description: str, extra: str = "") -> Path:
    """Helper: write a SKILL.md file with given metadata."""
    path = dir / "skills" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""---
name: {name}
description: {description}
{extra}
---

# {name.title()}

Body of {name}.
"""
    path.write_text(content)
    return path


def test_skills_search_path_shadow(tmp_path):
    """Project skill shadows global skill by name; non-conflicting both load."""
    from aede.skills.loader import load_skills

    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"

    _write_skill(global_dir, "shared", "Global version")
    _write_skill(project_dir, "shared", "Project version (overrides)")
    _write_skill(project_dir, "unique", "Only in project")

    registry = load_skills(global_dir=global_dir, project_dir=project_dir)

    assert "shared" in registry
    assert registry["shared"].description == "Project version (overrides)"
    assert "unique" in registry
    assert registry["unique"].description == "Only in project"


def test_skills_search_path_global_only(tmp_path):
    """Only global dir has skills; they load."""
    from aede.skills.loader import load_skills

    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)

    _write_skill(global_dir, "alpha", "Global alpha")

    registry = load_skills(global_dir=global_dir, project_dir=project_dir)
    assert "alpha" in registry
    assert registry["alpha"].description == "Global alpha"


def test_skills_search_path_empty(tmp_path):
    """No skills in either dir returns empty dict."""
    from aede.skills.loader import load_skills

    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"
    global_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)

    registry = load_skills(global_dir=global_dir, project_dir=project_dir)
    assert registry == {}


def test_skills_search_path_skips_non_md(tmp_path):
    """Non-.md files in skills dir are ignored."""
    from aede.skills.loader import load_skills

    global_dir = tmp_path / "global"
    (global_dir / "skills").mkdir(parents=True)
    (global_dir / "skills" / "readme.txt").write_text("not a skill")

    registry = load_skills(global_dir=global_dir, project_dir=tmp_path / "project")
    assert registry == {}
