"""
Three-tier code revert utility for rewind.

Priority:
  1. ``git stash create`` — safe (writes a commit object without touching the
     working tree, unlike ``git stash`` which had data-loss bug #68315).
  2. Reverse replay of ``old_string``/``new_string`` from tool_calls, with a
     hash guard that warns on external edits.
  3. Return shell tool calls that cannot be reverted, for manual cleanup.
"""
from __future__ import annotations
import hashlib
import subprocess
import warnings
from pathlib import Path
from typing import Any


def revert_code(project_dir: Path, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Three-tier revert. Tries git stash-create first, then reverse replay,
    and returns a list of non-revertible shell tool calls.

    Args:
        project_dir: The project root directory.
        tool_calls: List of tool call dicts with ``name`` and ``args`` keys.

    Returns:
        List of shell tool calls that could not be reverted (for manual cleanup).
    """
    shell_calls: list[dict[str, Any]] = []
    for tc in tool_calls:
        if tc.get("name") in ("powershell", "shell", "cmd"):
            shell_calls.append(tc)

    if _try_git_stash_create(project_dir):
        return shell_calls

    _try_reverse_replay(project_dir, tool_calls)

    return shell_calls


def _try_git_stash_create(project_dir: Path) -> bool:
    """Snapshot the dirty working tree via ``git stash create``, then restore
    all tracked files to HEAD.

    ``git stash create`` is safe because it writes a commit object into the
    object database *without* touching the working tree — unlike ``git stash``
    (which Claude Code hit data-loss bug #68315 on).  The orphan commit can
    be recovered via ``git fsck --lost-found`` if needed.

    Returns True if the snapshot + restore succeeded, False if there were no
    changes or git was not available.
    """
    try:
        rev = subprocess.run(
            ["git", "stash", "create"],
            cwd=str(project_dir),
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if not rev:
            return False
        # Restore tracked files to HEAD — this undoes all uncommitted changes.
        subprocess.run(
            ["git", "checkout", "HEAD", "--", "."],
            cwd=str(project_dir), check=True, capture_output=True, text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _try_reverse_replay(project_dir: Path, tool_calls: list[dict]) -> None:
    """Iterate ``tool_calls`` in reverse, undoing each write/create operation.

    For ``write_file``: write back ``old_string``.
    For ``create_file``: unlink the file.

    Before writing, hash-compare current file content to ``new_string`` to
    detect external edits.  If a mismatch is found, issue a ``UserWarning``
    and still proceed with the revert (the warning is informational).
    """
    for tc in reversed(tool_calls):
        name = tc.get("name", "")
        args = tc.get("args", {})
        if name not in ("write_file", "create_file", "edit"):
            continue
        path_str = args.get("path", "")
        if not path_str:
            continue
        path = project_dir / path_str

        if not path.exists() or not path.is_file():
            continue

        current = path.read_text(encoding="utf-8", errors="replace")

        if name == "write_file":
            expected = args.get("new_string", "")
            if _sha256(current) != _sha256(expected):
                warnings.warn(
                    f"{path} was modified outside aede; "
                    f"revert may produce unexpected results",
                    UserWarning,
                    stacklevel=2,
                )
            old = args.get("old_string", "")
            if old:
                path.write_text(old, encoding="utf-8")
            else:
                path.unlink()
        elif name == "edit":
            old = args.get("new_string", "")
            expected = args.get("old_string", "")
            if _sha256(current) != _sha256(old):
                warnings.warn(
                    f"{path} was modified outside aede; "
                    f"revert may produce unexpected results",
                    UserWarning,
                    stacklevel=2,
                )
            if old:
                path.write_text(current.replace(old, expected, 1), encoding="utf-8")
        elif name == "create_file":
            path.unlink()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()
