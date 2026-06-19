"""
Plan-mode artifact tools: write and read plan files for reviewable plans.

Plan files live in ``<project_dir>/docs-internal/plans/<session_id>.md``.
They are human-editable markdown files that survive session restarts and
context compaction, acting as the review checkpoint before code is written.
"""
from __future__ import annotations

from pathlib import Path


def write_plan_artifact(args: dict, project_dir: Path, session_id: str) -> str:
    """Write or update the plan artifact for the current session.

    Creates the plan file at ``docs-internal/plans/<session-id>.md`` inside
    the project directory.  If the file already exists it is overwritten.

    Args:
        args: Must contain ``content`` (str) — the full plan markdown.
        project_dir: The project root directory.
        session_id: The current session ULID.

    Returns:
        A confirmation string with the file path.
    """
    content = args.get("content", "")
    if not content:
        return "[write_plan_artifact: content is empty — nothing written]"

    plans_dir = project_dir / "docs-internal" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    filepath = plans_dir / f"{session_id}.md"
    filepath.write_text(content, encoding="utf-8")

    return f"Plan artifact written: {filepath} ({len(content)} chars)"


def read_plan_artifact(args: dict, project_dir: Path, session_id: str) -> str:
    """Read the plan artifact for the current session.

    Reads ``docs-internal/plans/<session-id>.md``. Returns the content or
    a message if the file does not exist.

    Args:
        args: May contain optional ``session_id`` to read a different plan.
              If omitted, uses the current session.
        project_dir: The project root directory.
        session_id: The current session ULID (fallback).

    Returns:
        The plan file content, or a status message if it doesn't exist.
    """
    target_sid = args.get("session_id", session_id)
    filepath = project_dir / "docs-internal" / "plans" / f"{target_sid}.md"

    if not filepath.exists():
        return f"[read_plan_artifact: no plan found for session {target_sid}]"

    return filepath.read_text(encoding="utf-8")


def write_progress(args: dict, project_dir: Path, session_id: str) -> str:
    """Append a progress entry to the progress file for the current session.

    Progress files track step completion during multi-step task execution.
    The file is at ``docs-internal/plans/<session-id>-progress.md``.

    Args:
        args: Must contain ``content`` (str) — the progress update to append.
        project_dir: The project root directory.
        session_id: The current session ULID.

    Returns:
        A confirmation string.
    """
    content = args.get("content", "")
    if not content:
        return "[write_progress: content is empty — nothing written]"

    plans_dir = project_dir / "docs-internal" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    filepath = plans_dir / f"{session_id}-progress.md"

    import datetime
    timestamp = datetime.datetime.now().isoformat()
    entry = f"\n---\n## {timestamp}\n\n{content}\n"

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry)

    return f"Progress updated: {filepath} ({len(content)} chars)"
