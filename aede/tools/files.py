"""
Filesystem tool implementations: read, write, create, and list.

Each function accepts an ``args`` dict (as received from the LLM tool-call
input) and returns a plain string result.  Errors are raised as built-in
exceptions so the router can catch them and return them to the model.
"""
from __future__ import annotations
from pathlib import Path
import datetime


def read_file(args: dict) -> str:
    """Return the UTF-8 contents of the file at ``args["path"]``.

    Raises:
        FileNotFoundError: if the path does not exist.
    """
    path = Path(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def write_file(args: dict) -> str:
    """Overwrite an existing file with ``args["content"]``.

    Raises:
        FileNotFoundError: if the file does not exist (use ``create_file`` instead).
    """
    path = Path(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}. Use create_file to create new files.")
    path.write_text(args["content"], encoding="utf-8")
    return f"Written: {path}"


def create_file(args: dict) -> str:
    """Create a new file at ``args["path"]`` with ``args["content"]``.

    Parent directories are created automatically.

    Raises:
        FileExistsError: if the file already exists (use ``write_file`` instead).
    """
    path = Path(args["path"])
    if path.exists():
        raise FileExistsError(f"File already exists: {path}. Use write_file to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"Created: {path}"


def list_dir(args: dict) -> str:
    """List directory contents up to ``args.get("depth", 1)`` levels deep.

    Returns a multi-line string with file sizes and modification times.
    Returns ``"(empty)"`` for empty directories.

    Raises:
        FileNotFoundError: if ``args["path"]`` does not exist.
    """
    path = Path(args["path"])
    depth = int(args.get("depth", 1))
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    lines: list[str] = []
    _walk(path, depth, 0, lines)
    return "\n".join(lines) if lines else "(empty)"


def _walk(path: Path, max_depth: int, current_depth: int, lines: list[str]) -> None:
    """Recursively append indented directory entries to ``lines``."""
    indent = "  " * current_depth
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
    except PermissionError:
        lines.append(f"{indent}[permission denied]")
        return
    for entry in entries:
        stat = entry.stat()
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        size = stat.st_size
        if entry.is_dir():
            lines.append(f"{indent}{entry.name}/  ({mtime})")
            if current_depth < max_depth - 1:
                _walk(entry, max_depth, current_depth + 1, lines)
        else:
            lines.append(f"{indent}{entry.name}  {size}B  {mtime}")
