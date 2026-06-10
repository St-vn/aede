"""
Project-level instruction discovery for aede.

Loads three tiers of instructions into the agent's system prompt:

1. **SOUL.md** (``~/.aede/SOUL.md``) — agent identity, tone, boundaries.
   Always loaded, never project-specific.

2. **Global AGENTS.md** (``~/.aede/AGENTS.md``) — cross-project user preferences.

3. **Project AGENTS.md / CLAUDE.md** — walks from git root to CWD, picking up
   ``AGENTS.md`` (preferred) or ``CLAUDE.md`` (fallback) in each directory.
   Concatenated root-to-CWD so closer files override earlier ones.
"""
from __future__ import annotations

from pathlib import Path


INSTRUCTION_FILENAMES = ("AGENTS.md", "CLAUDE.md")


def load_soul(home: Path) -> str | None:
    """Read ``~/.aede/SOUL.md`` if it exists.

    Returns the stripped content, or ``None`` if the file is missing or empty.
    """
    path = home / "SOUL.md"
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def load_global_instructions(home: Path) -> str | None:
    """Read ``~/.aede/AGENTS.md`` if it exists.

    Returns the stripped content, or ``None`` if the file is missing or empty.
    """
    path = home / "AGENTS.md"
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def _find_git_root(path: Path) -> Path | None:
    """Walk up from *path* looking for a ``.git`` directory or file.

    Returns the ancestor that contains ``.git``, or ``None`` if none is found.
    """
    for ancestor in [path] + list(path.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return None


def discover_project_instructions(project_dir: Path) -> list[tuple[Path, str]]:
    """Walk from the git root to *project_dir* finding instruction files.

    In each directory (git root first, then subdirectories down to
    *project_dir* inclusive), checks for ``AGENTS.md`` first, then falls
    back to ``CLAUDE.md``.  At most one file per directory is included.

    If no git root is found, only *project_dir* itself is checked.

    Returns a list of ``(path, content)`` tuples ordered from the most
    general directory to the most specific (closest to *project_dir*).
    """
    git_root = _find_git_root(project_dir)
    if git_root is None:
        git_root = project_dir

    try:
        relative = project_dir.relative_to(git_root)
    except ValueError:
        # project_dir is not under git_root — just check project_dir
        relative = Path(".")

    parts = relative.parts
    results: list[tuple[Path, str]] = []

    for i in range(len(parts) + 1):
        current = git_root.joinpath(*parts[:i]) if i > 0 else git_root
        for name in INSTRUCTION_FILENAMES:
            path = current / name
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    results.append((path, content))
                break

    return results


def build_instructions_suffix(home: Path, project_dir: Path) -> str | None:
    """Assemble the full instructions block for injection into the system prompt.

    Order:
      1. SOUL.md — identity/tone (if present)
      2. Global AGENTS.md — cross-project preferences (if present)
      3. Project instructions — ``AGENTS.md`` / ``CLAUDE.md`` chain (if any)

    Returns ``None`` when no instruction files are found.
    """
    parts: list[str] = []

    soul = load_soul(home)
    if soul:
        parts.append("## Identity\n" + soul)

    global_inst = load_global_instructions(home)
    if global_inst:
        parts.append("## Global Instructions\n" + global_inst)

    project_insts = discover_project_instructions(project_dir)
    for path, content in project_insts:
        label = path.parent.name or path.parent.drive or "project"
        parts.append(f"## Project Instructions ({label})\n" + content)

    return "\n\n".join(parts) if parts else None
