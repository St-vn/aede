from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from aede.import_ import slugify_or_fallback, safe_dest_path

_UNSUPPORTED_FIELDS = {
    "permissionMode", "mcpServers", "memory", "isolation",
    "effort", "color", "hooks",
}


@dataclass
class ImportReport:
    name: str
    dest_path: Path
    was_skipped: bool = False
    format: str = "Claude Code"
    warnings: list[str] = field(default_factory=list)


def import_claude_code_agent(
    src_path: Path,
    dest_dir: Path,
    _input_fn: Callable[[str], str] | None = None,
) -> ImportReport:
    import yaml

    text = src_path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(f"Source file {src_path} has no YAML frontmatter")

    parts = text.split("---", 2)
    raw_yaml = parts[1].strip()
    body = parts[2].strip() if len(parts) >= 3 else ""

    meta: dict[str, Any] = yaml.safe_load(raw_yaml) or {}
    name: str = slugify_or_fallback(meta.get("name", "") or src_path.stem, fallback=src_path.stem)

    supported = {}
    unsupported_lines = []

    for key, value in meta.items():
        if key in _UNSUPPORTED_FIELDS:
            yaml_line = yaml.safe_dump({key: value}, default_flow_style=False).strip()
            unsupported_lines.append(f"# {yaml_line}")
        else:
            supported[key] = value

    dest_path = safe_dest_path(dest_dir, name)

    if dest_path.exists():
        if _input_fn is None:
            raw = input(f"Overwrite {dest_path}? [y/N] ")
        else:
            raw = _input_fn(f"Overwrite {dest_path}? [y/N] ")
        if raw.lower() != "y":
            return ImportReport(name=name, dest_path=dest_path, was_skipped=True)

    frontmatter_lines = ["---"]
    for key, value in supported.items():
        dumped = yaml.safe_dump({key: value}, default_flow_style=False).strip()
        frontmatter_lines.append(dumped)
    frontmatter_lines.extend(unsupported_lines)
    frontmatter_lines.append("---")

    output_text = "\n".join(frontmatter_lines) + "\n\n" + body
    dest_path.write_text(output_text, encoding="utf-8")

    return ImportReport(name=name, dest_path=dest_path)
