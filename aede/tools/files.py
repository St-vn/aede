"""
Filesystem tool implementations: read, write, create, and list.

Each function accepts an ``args`` dict (as received from the LLM tool-call
input) and returns a plain string result.  Errors are raised as built-in
exceptions so the router can catch them and return them to the model.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import datetime


def read_file(args: dict, sandbox: Any = None, fileset: Any = None) -> str:
    """Return the UTF-8 contents of the file at ``args["path"]``.

    Supports optional ``offset`` (1-indexed start line) and ``limit``
    (max lines to return). When omitted, returns up to 2000 lines.

    Args:
        sandbox: Optional ``DockerSandbox`` instance.  When set, the path is
            translated to its container equivalent.
        fileset: Optional ``FileSet`` instance.  When set, write paths are
            checked against the declared set.

    Raises:
        FileNotFoundError: if the path does not exist.
    """
    path = Path(args["path"])
    if sandbox is not None:
        container_path = sandbox.translate_path(path)
    else:
        container_path = path
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines(keepends=True)

    offset = args.get("offset")
    limit = args.get("limit")

    if offset is not None or limit is not None:
        start = (offset - 1) if offset is not None else 0
        if limit is not None:
            end = start + limit
        else:
            end = len(lines)
        start = max(0, min(start, len(lines)))
        end = max(start, min(end, len(lines)))
        selected = lines[start:end]
        result = "".join(selected)
        total_lines = len(lines)
        return f"<file {path} lines {start + 1}–{end} of {total_lines}>\n{result}"
    else:
        if len(lines) > 2000:
            truncated = "".join(lines[:2000])
            return f"<file {path} lines 1–2000 of {len(lines)}>\n{truncated}\n[... file truncated at 2000 lines — use offset/limit to read more]"
        return content


def write_file(args: dict, sandbox: Any = None, fileset: Any = None) -> str:
    """Overwrite an existing file with ``args["content"]``.

    Args:
        sandbox: Optional ``DockerSandbox`` instance.  When set, the path is
            translated to its container equivalent and a fileset is required —
            sandbox mode without a fileset is an unsafe configuration that is
            rejected to prevent unbounded host writes.
        fileset: Optional ``FileSet`` instance.  When set, write paths are
            checked against the declared set.

    Raises:
        FileNotFoundError: if the file does not exist (use ``create_file`` instead).
    """
    path = Path(args["path"])
    if sandbox is not None:
        # Sandbox active: all host writes MUST be gated by a fileset.
        # Without a fileset there is no declared boundary, so reject the write.
        if fileset is None:
            return (
                f"Write to {path} rejected: sandbox is active but no fileset has been "
                f"declared.  Call declare_fileset first to specify which paths may be written."
            )
        container_path = sandbox.translate_path(path)  # noqa: F841 — recorded for audit
    if fileset is not None:
        if not fileset.is_writable(str(path)):
            return f"Write to {path} is outside declared fileset. Use declare_fileset to widen."
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}. Use create_file to create new files.")
    path.write_text(args["content"], encoding="utf-8")
    return f"Written: {path}"


def create_file(args: dict, sandbox: Any = None, fileset: Any = None) -> str:
    """Create a new file at ``args["path"]`` with ``args["content"]``.

    Parent directories are created automatically.

    Args:
        sandbox: Optional ``DockerSandbox`` instance.  When set, the path is
            translated to its container equivalent and a fileset is required —
            sandbox mode without a fileset is an unsafe configuration that is
            rejected to prevent unbounded host writes.
        fileset: Optional ``FileSet`` instance.  When set, write paths are
            checked against the declared set.

    Raises:
        FileExistsError: if the file already exists (use ``write_file`` instead).
    """
    path = Path(args["path"])
    if sandbox is not None:
        # Sandbox active: all host writes MUST be gated by a fileset.
        if fileset is None:
            return (
                f"Create {path} rejected: sandbox is active but no fileset has been "
                f"declared.  Call declare_fileset first to specify which paths may be written."
            )
        container_path = sandbox.translate_path(path)  # noqa: F841 — recorded for audit
    if fileset is not None:
        if not fileset.is_writable(str(path)):
            return f"Write to {path} is outside declared fileset. Use declare_fileset to widen."
    if path.exists():
        raise FileExistsError(f"File already exists: {path}. Use write_file to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"Created: {path}"


def edit(args: dict, sandbox: Any = None, fileset: Any = None) -> str:
    """Exact-match string replacement tool.

    Args:
        path: File path.
        old_string: Exact text to find (must be unique unless replace_all).
        new_string: Replacement text.
        replace_all: If True, replace ALL occurrences of old_string (default False).
    """
    path = Path(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    old = args["old_string"]
    new = args["new_string"]
    replace_all = args.get("replace_all", False)
    content = path.read_text(encoding="utf-8", errors="replace")
    if replace_all:
        if old not in content:
            raise ValueError(f"old_string not found in {path}")
        new_content = content.replace(old, new)
    else:
        count = content.count(old)
        if count == 0:
            raise ValueError(f"old_string not found in {path}")
        if count > 1:
            raise ValueError(f"old_string appears {count} times in {path}. Use replace_all=True or include more surrounding context for a unique match.")
        new_content = content.replace(old, new, 1)
    path.write_text(new_content, encoding="utf-8")
    return f"Edited: {path}"


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


def glob_files(args: dict, sandbox: Any = None, fileset: Any = None) -> str:
    """Find files matching a glob pattern, sorted by mtime descending.

    Args:
        pattern: Glob pattern (e.g., ``**/*.tsx``, ``src/**/*.py``).
        path: Optional root directory (defaults to current working directory).

    Returns newline-separated list of matching files with mtime.
    """
    pattern = args["pattern"]
    root = Path(args.get("path", "."))
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    matches = []
    for p in root.rglob(pattern):
        if p.is_file():
            mtime = p.stat().st_mtime
            matches.append((p, mtime))

    matches.sort(key=lambda x: x[1], reverse=True)

    if not matches:
        return "(no matching files)"

    lines = []
    for p, mtime in matches:
        dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = p
        lines.append(f"{rel}  {dt}")
    return "\n".join(lines)
