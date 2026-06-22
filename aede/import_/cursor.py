from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Callable

from aede.import_.claude_code import ImportReport

_UNSUPPORTED_FIELDS = {"globs", "alwaysApply"}


def _slugify(text: str) -> str:
    """Lowercase, replace non-alphanumeric runs with a single hyphen, strip edges."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def import_cursor_mdc(
    src_path: Path,
    dest_dir: Path,
    _input_fn: Callable[[str], str] | None = None,
) -> ImportReport:
    """Import a Cursor .cursor/rules/*.mdc file into an aede agent .md file.

    The source .mdc has YAML frontmatter (description, globs, alwaysApply)
    followed by a markdown body.  Unsupported fields (globs, alwaysApply) are
    commented out in the output frontmatter.
    """
    import yaml

    text = src_path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(f"Source file {src_path} has no YAML frontmatter")

    parts = text.split("---", 2)
    raw_yaml = parts[1].strip()
    body = parts[2].strip() if len(parts) >= 3 else ""

    meta: dict[str, Any] = yaml.safe_load(raw_yaml) or {}

    name_slug = _slugify(src_path.stem)
    if not name_slug:
        name_slug = "imported-agent"

    description: str = meta.get("description") or "Imported from Cursor"

    dest_path = dest_dir / f"{name_slug}.md"

    if dest_path.exists():
        if _input_fn is None:
            raw = input(f"Overwrite {dest_path}? [y/N] ")
        else:
            raw = _input_fn(f"Overwrite {dest_path}? [y/N] ")
        if raw.lower() != "y":
            return ImportReport(
                name=name_slug,
                dest_path=dest_path,
                was_skipped=True,
                format="Cursor",
            )

    supported = {
        "name": name_slug,
        "description": description,
        "model": "inherit",
    }
    unsupported_lines = []

    for key, value in meta.items():
        if key in _UNSUPPORTED_FIELDS:
            yaml_line = yaml.safe_dump({key: value}, default_flow_style=False).strip()
            unsupported_lines.append(f"# {yaml_line}")

    frontmatter_lines = ["---"]
    for key, value in supported.items():
        dumped = yaml.safe_dump({key: value}, default_flow_style=False).strip()
        frontmatter_lines.append(dumped)
    frontmatter_lines.extend(unsupported_lines)
    frontmatter_lines.append("---")

    output_text = "\n".join(frontmatter_lines) + "\n\n" + body
    dest_path.write_text(output_text, encoding="utf-8")

    return ImportReport(name=name_slug, dest_path=dest_path, format="Cursor")
