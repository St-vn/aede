from __future__ import annotations
from pathlib import Path
import datetime


def read_file(args: dict) -> str:
    path = Path(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def write_file(args: dict) -> str:
    path = Path(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}. Use create_file to create new files.")
    path.write_text(args["content"], encoding="utf-8")
    return f"Written: {path}"


def create_file(args: dict) -> str:
    path = Path(args["path"])
    if path.exists():
        raise FileExistsError(f"File already exists: {path}. Use write_file to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"Created: {path}"


def list_dir(args: dict) -> str:
    path = Path(args["path"])
    depth = int(args.get("depth", 1))
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    lines: list[str] = []
    _walk(path, depth, 0, lines)
    return "\n".join(lines) if lines else "(empty)"


def _walk(path: Path, max_depth: int, current_depth: int, lines: list[str]) -> None:
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
