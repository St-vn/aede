from __future__ import annotations
from pathlib import Path
from typing import Any, Callable

from aede.import_.claude_code import ImportReport

_UNSUPPORTED_FIELDS = {
    "hidden",
}

_FIELD_MAP = {
    "allowed-tools": "allowed_tools",
    "trigger": "trigger_phrases",
}


def import_claude_code_skill(
    src_path: Path,
    dest_dir: Path,
    _input_fn: Callable[[str], str] | None = None,
    source: str = "Claude Code",
) -> ImportReport:
    """Import a Claude Code skill into aede SKILL.md format.

    The ``source`` parameter lets callers tag the originating tool so that
    ``ImportReport.format`` reflects the real importer (e.g. "Antigravity",
    "Windsurf", "Codex").  It defaults to "Claude Code" so all existing
    callers remain unaffected.
    """
    import yaml

    if src_path.is_dir():
        skill_file = src_path / "SKILL.md"
        if not skill_file.exists():
            raise ValueError(f"Directory {src_path} has no SKILL.md inside")
        src_path = skill_file

    text = src_path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(f"Source file {src_path} has no YAML frontmatter")

    parts = text.split("---", 2)
    raw_yaml = parts[1].strip()
    body = parts[2].strip() if len(parts) >= 3 else ""

    meta: dict[str, Any] = yaml.safe_load(raw_yaml) or {}
    name: str = meta.get("name", src_path.stem)

    supported = {}
    unsupported_lines = []

    for key, value in meta.items():
        if key in _UNSUPPORTED_FIELDS:
            yaml_line = yaml.safe_dump({key: value}, default_flow_style=False).strip()
            unsupported_lines.append(f"# {yaml_line}")
        else:
            mapped_key = _FIELD_MAP.get(key, key)
            supported[mapped_key] = value

    dest_path = dest_dir / f"{name}.md"

    if dest_path.exists():
        if _input_fn is None:
            raw = input(f"Overwrite {dest_path}? [y/N] ")
        else:
            raw = _input_fn(f"Overwrite {dest_path}? [y/N] ")
        if raw.lower() != "y":
            return ImportReport(name=name, dest_path=dest_path, was_skipped=True, format=source)

    frontmatter_lines = ["---"]
    for key, value in supported.items():
        dumped = yaml.safe_dump({key: value}, default_flow_style=False).strip()
        frontmatter_lines.append(dumped)
    frontmatter_lines.extend(unsupported_lines)
    frontmatter_lines.append("---")

    output_text = "\n".join(frontmatter_lines) + "\n\n" + body
    dest_path.write_text(output_text, encoding="utf-8")

    return ImportReport(name=name, dest_path=dest_path, format=source)
