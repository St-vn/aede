"""
Search tools for aede: file search (ripgrep) and session history search (FTS5).
"""
from __future__ import annotations
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aede.db import DB


def search_files(args: dict) -> str:
    """Search for a regex pattern in files under a directory using ripgrep.

    Args:
        args: Must contain ``"pattern"`` (regex) and ``"path"`` (directory or file).

    Returns:
        Matching lines in ``file:line:content`` format, or ``"(no matches)"``
        if nothing was found.

    Raises:
        RuntimeError: if ripgrep exits with an error code, or if ``rg`` is not
            installed.
    """
    pattern = args["pattern"]
    path = args["path"]

    try:
        result = subprocess.run(
            ["rg", "--line-number", "--with-filename", pattern, path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout or "(no matches)"
        if result.returncode == 1:
            return "(no matches)"
        raise RuntimeError(f"ripgrep error: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("ripgrep (rg) not found. Install ripgrep: https://github.com/BurntSushi/ripgrep")


def session_search(args: dict, db: "DB | None" = None) -> str:
    """Search past session message history by keyword using FTS5.

    Args:
        args: Must contain ``"query"`` (keyword/phrase).  Optional ``"limit"``
            (integer, default 10) caps the number of hit messages returned.
        db: The ``DB`` instance to query.  If ``None``, raises ``RuntimeError``.

    Returns:
        A human-readable string summarising each result group (session metadata,
        context window messages, and bookends), suitable for the model to read.

    Raises:
        RuntimeError: if ``db`` is not provided.
    """
    if db is None:
        raise RuntimeError(
            "session_search requires a database connection — "
            "ToolRouter was not initialised with db=."
        )

    query: str = args["query"]
    limit: int = int(args.get("limit", 10))

    groups = db.search_messages(query=query, limit=limit)

    if not groups:
        return f"(no results for query: {query!r})"

    lines: list[str] = []
    for i, group in enumerate(groups, 1):
        lines.append(
            f"--- Result {i} | session: {group['session_id']} "
            f"| title: {group['session_title']!r} "
            f"| created: {group['session_created_at']} ---"
        )
        lines.append("  [context window (±5 messages around hit)]")
        for msg in group["context"]:
            marker = " <-- HIT" if msg["id"] == group["hit"]["id"] else ""
            lines.append(f"  [{msg['role']}] {msg['content']}{marker}")
        if group["bookends"]:
            lines.append("  [session bookends]")
            for msg in group["bookends"]:
                lines.append(f"  [{msg['role']}] {msg['content']}")
        lines.append("")

    return "\n".join(lines)
