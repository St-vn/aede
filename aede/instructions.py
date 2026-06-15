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

import re
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


@dataclass
class VoiceDef:
    engine: str | None = None
    voice_id: str | None = None
    rate: float = 1.0
    pitch: float = 1.0


@dataclass
class SoulDef:
    name: str | None = None
    phonetic: str | None = None
    wake_word: str | None = None
    wake_word_phonetic: str | None = None
    persona: str = ""
    voice: VoiceDef = field(default_factory=VoiceDef)
    aliases: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n?---\n?", re.DOTALL)
_warned_paths: set[Path] = set()


def _warn(console: Any, msg: str) -> None:
    if console is not None:
        console.print(msg)
    else:
        print(msg)


def _parse_frontmatter(text: str, *, console: Any = None) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    block = m.group(1)
    body = text[m.end():]

    import yaml

    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError:
        _warn(console, "[yellow]⚠ SOUL.md frontmatter invalid, ignoring[/yellow]")
        return {}, body

    if not isinstance(parsed, dict):
        _warn(console, "[yellow]⚠ SOUL.md frontmatter is not a mapping, ignoring[/yellow]")
        return {}, body

    return parsed, body


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


def _coerce_voice(raw: Any) -> "VoiceDef":
    if not isinstance(raw, dict):
        return VoiceDef()
    rate_raw = raw.get("rate", 1.0)
    pitch_raw = raw.get("pitch", 1.0)
    try:
        rate = float(rate_raw)
    except (TypeError, ValueError):
        rate = 1.0
    try:
        pitch = float(pitch_raw)
    except (TypeError, ValueError):
        pitch = 1.0
    return VoiceDef(
        engine=raw.get("engine"),
        voice_id=raw.get("voice_id"),
        rate=rate,
        pitch=pitch,
    )


def _def_from_frontmatter(fm: dict, body: str, source_path: Path | None,
                           warn_console: Any = None) -> SoulDef:
    if not fm:
        return SoulDef(
            persona=body,
            source_files=[str(source_path)] if source_path else [],
        )
    raw_voice = fm.get("voice") or {}
    return SoulDef(
        name=fm.get("name"),
        phonetic=fm.get("phonetic"),
        wake_word=fm.get("wake_word"),
        wake_word_phonetic=fm.get("wake_word_phonetic"),
        persona=body,
        voice=_coerce_voice(raw_voice),
        aliases=list(fm.get("aliases") or []),
        source_files=[str(source_path)] if source_path else [],
    )


def load_soul_def(home: Path, project_dir: Path | None, *, console: Any = None) -> SoulDef:
    global_path = home / "SOUL.md"
    project_path = (project_dir / "SOUL.md") if project_dir is not None else None

    global_fm, global_body, global_present = {}, "", False
    if global_path.exists():
        global_present = True
        try:
            text = global_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise
        if global_path not in _warned_paths:
            global_fm, global_body = _parse_frontmatter(text, console=console)
            _warned_paths.add(global_path)

    project_fm, project_body, project_present = {}, "", False
    if project_path is not None and project_path.exists():
        project_present = True
        try:
            text = project_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise
        if project_path not in _warned_paths:
            project_fm, project_body = _parse_frontmatter(text, console=console)
            _warned_paths.add(project_path)

    if not global_present and not project_present:
        return SoulDef()

    merged_fm = {**global_fm, **project_fm}
    body = project_body if project_present else global_body
    source_files: list[str] = []
    if global_present:
        source_files.append(str(global_path))
    if project_present:
        source_files.append(str(project_path))

    if not merged_fm:
        return SoulDef(persona=body, source_files=source_files)

    return SoulDef(
        name=merged_fm.get("name"),
        phonetic=merged_fm.get("phonetic"),
        wake_word=merged_fm.get("wake_word"),
        wake_word_phonetic=merged_fm.get("wake_word_phonetic"),
        persona=body,
        voice=_coerce_voice(merged_fm.get("voice") or {}),
        aliases=list(merged_fm.get("aliases") or []),
        source_files=source_files,
    )
