from __future__ import annotations
from pathlib import Path

from aede.skills.schema import SkillDef


_SKILL_EXTS = {".md", ".skill"}


def _scan_dir(skills_dir: Path) -> dict[str, SkillDef]:
    """Scan a single skills directory and return {name -> SkillDef}."""
    registry: dict[str, SkillDef] = {}
    if not skills_dir.is_dir():
        return registry
    for child in sorted(skills_dir.iterdir()):
        if child.suffix.lower() in _SKILL_EXTS or (child.is_dir() and (child / "SKILL.md").exists()):
            md_path = child if child.suffix.lower() in _SKILL_EXTS else child / "SKILL.md"
            try:
                sd = SkillDef.from_file(md_path)
                registry[sd.name] = sd
            except Exception as e:
                import sys
                print(f"[yellow]⚠ Skill load error in {md_path.name}: {e}[/yellow]", file=sys.stderr)
    return registry


def load_skills(
    global_dir: Path,
    project_dir: Path,
    include_claude_fallback: bool = True,
) -> dict[str, SkillDef]:
    """Scan global and project skills dirs, return {name -> SkillDef}.

    When ``include_claude_fallback`` is true (the default for the running app),
    also scans ``~/.claude/skills`` for skills shared with Claude Code.  Tests
    that pass explicit temp dirs set it false to keep loading hermetic.
    Project skills shadow global skills with the same name.
    """
    global_skills_dir = global_dir / "skills"
    project_skills_dir = project_dir / "skills"

    registry: dict[str, SkillDef] = {}
    registry.update(_scan_dir(global_skills_dir))
    registry.update(_scan_dir(project_skills_dir))
    if include_claude_fallback:
        claude_skills = Path.home() / ".claude" / "skills"
        if claude_skills != global_skills_dir and claude_skills != project_skills_dir:
            registry.update(_scan_dir(claude_skills))
    return registry
