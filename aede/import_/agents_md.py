from __future__ import annotations
from pathlib import Path
from typing import Callable

from aede.import_ import slugify
from aede.import_.claude_code import ImportReport

_GENERIC_NAMES = {"agents.md", "gemini.md"}


def import_agents_md(
    src_path: Path,
    dest_dir: Path,
    source: str = "AGENTS.md",
    _input_fn: Callable[[str], str] | None = None,
) -> ImportReport:
    """Import a plain-markdown rules file (AGENTS.md, GEMINI.md, Windsurf .md)
    into an aede agent .md file.

    The source file has NO frontmatter — its entire content becomes the agent body.
    Name is synthesised from the parent directory when the filename is generic
    (AGENTS.md / GEMINI.md / agents.md case-insensitive), otherwise from the stem.
    """
    text = src_path.read_text(encoding="utf-8")

    filename_lower = src_path.name.lower()
    if filename_lower in _GENERIC_NAMES:
        raw_name = src_path.parent.name
    else:
        raw_name = src_path.stem

    name = slugify(raw_name)
    if not name:
        name = "imported-agent"

    description = f"Imported from {source}"

    dest_path = dest_dir / f"{name}.md"

    if dest_path.exists():
        if _input_fn is None:
            raw = input(f"Overwrite {dest_path}? [y/N] ")
        else:
            raw = _input_fn(f"Overwrite {dest_path}? [y/N] ")
        if raw.lower() != "y":
            return ImportReport(
                name=name,
                dest_path=dest_path,
                was_skipped=True,
                format=source,
            )

    import yaml

    frontmatter_fields = {
        "name": name,
        "description": description,
        "model": "inherit",
    }

    frontmatter_lines = ["---"]
    for key, value in frontmatter_fields.items():
        dumped = yaml.safe_dump({key: value}, default_flow_style=False).strip()
        frontmatter_lines.append(dumped)
    frontmatter_lines.append("---")

    body = text.strip()
    output_text = "\n".join(frontmatter_lines) + "\n\n" + body
    dest_path.write_text(output_text, encoding="utf-8")

    return ImportReport(name=name, dest_path=dest_path, format=source)
