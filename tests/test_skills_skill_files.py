import pytest
from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _skill_path(name: str) -> Path:
    """Return the path to a skill's SKILL.md under the project skills dir."""
    return SKILLS_DIR / name / "SKILL.md"


def test_sdlc_engineer_skill_loads():
    """sdlc-engineer skill loads with SkillDef.from_file."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("sdlc-engineer"))
    assert sd.name == "sdlc-engineer"
    assert sd.description
    assert sd.trigger_phrases
    assert sd.body


def test_sdlc_engineer_has_orchestration_body():
    """sdlc-engineer skill body contains orchestration instructions."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("sdlc-engineer"))
    assert len(sd.body) > 200
    assert "spec" in sd.body.lower() or "implement" in sd.body.lower()
    assert "design" in sd.body.lower() or "architecture" in sd.body.lower()


def test_configure_skill_loads():
    """configure skill loads with SkillDef.from_file."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("configure"))
    assert sd.name == "configure"
    assert sd.description
    assert sd.trigger_phrases
    assert sd.body


def test_configure_has_interview_body():
    """configure skill body contains interview or configuration logic."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("configure"))
    assert len(sd.body) > 200
    assert "question" in sd.body.lower() or "intent" in sd.body.lower() or "config" in sd.body.lower()


def test_research_skill_loads():
    """research skill loads with SkillDef.from_file."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("research"))
    assert sd.name == "research"
    assert sd.description
    assert sd.trigger_phrases
    assert sd.body


def test_research_has_track_body():
    """research skill body contains market/technical/compliance tracks."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("research"))
    assert len(sd.body) > 200
    assert "market" in sd.body.lower() or "technical" in sd.body.lower() or "compliance" in sd.body.lower()


def test_kaizen_skill_loads():
    """kaizen skill loads with SkillDef.from_file."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("kaizen"))
    assert sd.name == "kaizen"
    assert sd.description
    assert sd.trigger_phrases
    assert sd.body


def test_kaizen_has_critique_body():
    """kaizen skill body contains critique-then-fix format."""
    from aede.skills.schema import SkillDef

    sd = SkillDef.from_file(_skill_path("kaizen"))
    assert len(sd.body) > 200
    assert "symptom" in sd.body.lower() or "root" in sd.body.lower() or "lesson" in sd.body.lower()


def test_all_skills_have_descriptions():
    """All skill files have non-empty descriptions."""
    from aede.skills.schema import SkillDef

    skill_dirs = sorted(SKILLS_DIR.iterdir())
    assert len(skill_dirs) >= 4

    for sd_path in skill_dirs:
        if not sd_path.is_dir():
            continue
        skill_md = sd_path / "SKILL.md"
        if not skill_md.exists():
            continue
        sd = SkillDef.from_file(skill_md)
        assert sd.description, f"Skill {sd.name} has no description"


def test_all_skills_have_trigger_phrases():
    """All built-in skills have at least one trigger phrase."""
    from aede.skills.schema import SkillDef

    skill_dirs = sorted(SKILLS_DIR.iterdir())

    for sd_path in skill_dirs:
        if not sd_path.is_dir():
            continue
        skill_md = sd_path / "SKILL.md"
        if not skill_md.exists():
            continue
        sd = SkillDef.from_file(skill_md)
        assert sd.trigger_phrases, f"Skill {sd.name} has no trigger_phrases"


def test_builtin_skills_load_via_loader(tmp_path):
    """Built-in skills are discoverable via load_skills from the project dir."""
    from aede.skills.loader import load_skills

    global_dir = tmp_path / "global"
    project_dir = Path(__file__).resolve().parent.parent

    registry = load_skills(global_dir=global_dir, project_dir=project_dir)

    assert "sdlc-engineer" in registry
    assert "configure" in registry
    assert "research" in registry
    assert "kaizen" in registry


def test_plugin_filter_with_builtin_skills(tmp_path):
    """Plugin registry can filter built-in skills by name."""
    from aede.skills.loader import load_skills
    from aede.plugins.registry import filter_skills

    global_dir = tmp_path / "global"
    project_dir = Path(__file__).resolve().parent.parent

    registry = load_skills(global_dir=global_dir, project_dir=project_dir)

    filtered = filter_skills(registry, enabled=["sdlc-engineer", "research"])
    assert "sdlc-engineer" in filtered
    assert "research" in filtered
    assert "configure" not in filtered
    assert "kaizen" not in filtered
