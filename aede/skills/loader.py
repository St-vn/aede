from __future__ import annotations
from pathlib import Path

from aede.skills.schema import SkillDef, SkillLoadError


def _scan_dir(skills_dir: Path) -> dict[str, SkillDef]:
    """Scan a single skills directory and return {name -> SkillDef}."""
    registry: dict[str, SkillDef] = {}
    if not skills_dir.is_dir():
        return registry
    for child in sorted(skills_dir.iterdir()):
        if child.suffix.lower() == ".md" or (child.is_dir() and (child / "SKILL.md").exists()):
            md_path = child if child.suffix.lower() == ".md" else child / "SKILL.md"
            try:
                sd = SkillDef.from_file(md_path)
                registry[sd.name] = sd
            except SkillLoadError:
                pass
    return registry


def load_skills(global_dir: Path, project_dir: Path) -> dict[str, SkillDef]:
    """Scan global and project skills dirs, return {name -> SkillDef}.

    Project skills shadow global skills with the same name.
    """
    global_skills_dir = global_dir / "skills"
    project_skills_dir = project_dir / "skills"

    registry: dict[str, SkillDef] = {}
    registry.update(_scan_dir(global_skills_dir))
    registry.update(_scan_dir(project_skills_dir))
    return registry
