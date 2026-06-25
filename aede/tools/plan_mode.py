"""
Plan-mode artifact tools: write and read plan files for reviewable plans.

Plan files live in ``<project_dir>/docs-internal/plans/<session_id>.md``.
They are human-editable markdown files that survive session restarts and
context compaction, acting as the review checkpoint before code is written.
"""
from __future__ import annotations

import re
from pathlib import Path

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)


def _validate_session_id(sid: str) -> None:
    if not ULID_PATTERN.match(sid):
        raise ValueError(f"Invalid session_id: {sid!r} -- must be a valid ULID")


def _assert_path_in_project(filepath: Path, project_dir: Path) -> None:
    resolved = filepath.resolve()
    project_root = project_dir.resolve()
    if project_root.parent == project_root:
        raise ValueError("project_dir must not be a filesystem root")
    if not resolved.is_relative_to(project_root):
        raise ValueError(
            f"Plan path {resolved} escapes project directory {project_root}"
        )


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

    _validate_session_id(session_id)

    filepath = project_dir / "docs-internal" / "plans" / f"{session_id}.md"
    _assert_path_in_project(filepath, project_dir)

    filepath.parent.mkdir(parents=True, exist_ok=True)
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
    _validate_session_id(target_sid)

    if target_sid != session_id:
        raise ValueError(
            f"Cannot read plan for session {target_sid!r}: "
            f"not the current session {session_id!r}"
        )

    filepath = project_dir / "docs-internal" / "plans" / f"{target_sid}.md"
    _assert_path_in_project(filepath, project_dir)

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

    _validate_session_id(session_id)

    filepath = project_dir / "docs-internal" / "plans" / f"{session_id}-progress.md"
    _assert_path_in_project(filepath, project_dir)

    filepath.parent.mkdir(parents=True, exist_ok=True)

    import datetime
    timestamp = datetime.datetime.now().isoformat()
    entry = f"\n---\n## {timestamp}\n\n{content}\n"

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry)

    return f"Progress updated: {filepath} ({len(content)} chars)"
