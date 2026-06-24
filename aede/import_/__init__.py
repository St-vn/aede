from __future__ import annotations
import re
from pathlib import Path


_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def slugify(text: str) -> str:
    """Lowercase, replace non-alphanumeric runs with a single hyphen, strip edges."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def slugify_or_fallback(text: str, fallback: str) -> str:
    """Return slugify(text) if non-empty, else fallback."""
    slug = slugify(text)
    if not slug:
        return fallback
    return slug


def safe_dest_path(dest_dir: Path, name: str) -> Path:
    """Build a destination path, guarding against traversal and reserved names."""
    if name.lower() in _WINDOWS_RESERVED:
        name = name + "-"
    dest_path = dest_dir / f"{name}.md"
    resolved = dest_path.resolve()
    dest_resolved = dest_dir.resolve()
    if not resolved.is_relative_to(dest_resolved):
        raise ValueError(
            f"Destination path {resolved} escapes base directory {dest_resolved}"
        )
    return dest_path
