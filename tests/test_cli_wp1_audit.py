"""
WP-1 audit tests for aede/cli.py.

Covers findings from the holistic-audit judgment pass (2026-06-22):
  F2 — $EDITOR with embedded flags silently fails (issue #27)
  F3 — Recursive _run on /resume causes unbounded stack growth (issue #28)
"""
from __future__ import annotations

import json
import shlex
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# F2 — $EDITOR split: flags in EDITOR env must be tokenised before exec
# ---------------------------------------------------------------------------

class TestMemoryEditEditorSplit:
    """_memory_edit must split $EDITOR on whitespace so 'code --wait'
    reaches subprocess as ['code', '--wait', path] — not as a single
    binary name (issue #27)."""

    def test_editor_with_flags_splits_correctly(self):
        """Confirm shlex.split('code --wait') gives ['code', '--wait'] so
        subprocess.run receives a valid list — NOT the whole string as one token."""
        editor_value = "code --wait"
        expected_cmd_prefix = shlex.split(editor_value)
        assert expected_cmd_prefix == ["code", "--wait"], (
            "shlex.split must tokenise the editor string so flags are separate args"
        )

    def test_single_word_editor_unchanged(self):
        """A simple editor like 'vi' or 'notepad.exe' must not be altered."""
        assert shlex.split("vi") == ["vi"]
        assert shlex.split("notepad.exe") == ["notepad.exe"]

    def test_memory_edit_passes_split_editor_to_subprocess(self, monkeypatch):
        """_memory_edit must pass shlex.split(editor) + [path] to subprocess.run,
        NOT [editor, path] where editor is the unsplit string.

        Confirmed RED against current code: cmd[0] = 'code --wait' (unsplit).
        After the fix, cmd[0] must be 'code' and cmd[1] must be '--wait'.
        """
        from aede.cli import _memory_edit

        record = {"id": "abc", "type": "antipattern", "content": "do not do X"}
        store = MagicMock()
        store.get.return_value = record
        store.update = MagicMock()

        captured_calls: list[list[str]] = []

        def _patched_run(cmd, **kwargs):
            captured_calls.append(list(cmd))
            # Write valid JSON back to the temp file path (last element of cmd)
            # so _memory_edit's read step succeeds and store.update is called.
            try:
                Path(cmd[-1]).write_text(json.dumps(record), encoding="utf-8")
            except Exception:
                pass
            return MagicMock(returncode=0)

        monkeypatch.setenv("EDITOR", "code --wait")
        with patch("subprocess.run", side_effect=_patched_run):
            _memory_edit(store, "abc")

        assert captured_calls, "subprocess.run must have been called"
        cmd = captured_calls[0]
        # After fix: first token must be 'code', second '--wait'
        assert cmd[0] == "code", (
            f"First token must be 'code' (editor binary), got {cmd!r}. "
            "Likely cause: $EDITOR string was not split with shlex before passing to subprocess."
        )
        assert cmd[1] == "--wait", (
            f"Second token must be '--wait' (editor flag), got {cmd!r}."
        )
        assert cmd[-1].endswith(".json"), (
            f"Last token must be the temp file path (.json), got {cmd!r}."
        )


# ---------------------------------------------------------------------------
# F3 — _run resume: stack growth — structural regression guard
# ---------------------------------------------------------------------------

class TestRunResumeStackGrowth:
    """_run must NOT recurse into itself on /resume — it should either
    return the resume target for the caller to loop, or use a loop internally.

    This structural test guards against re-introduction of the recursive
    `return await _run(resume_session_id=...)` pattern (issue #28)."""

    def test_resume_is_not_tail_recursive_in_source(self):
        """Structural check: the fix must replace the recursive
        `return await _run(resume_session_id=resume_target)` pattern with
        either a return value or a loop.

        If this test fails, the recursive call has been re-introduced."""
        import ast
        import pathlib

        src = pathlib.Path("aede/cli.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                # Look for: return await _run(...)
                val = node.value
                if (
                    val is not None
                    and isinstance(val, ast.Await)
                    and isinstance(val.value, ast.Call)
                ):
                    func = val.value.func
                    if isinstance(func, ast.Name) and func.id == "_run":
                        # Recursive call found — check if resume_session_id is being passed
                        for kw in val.value.keywords:
                            if kw.arg == "resume_session_id":
                                pytest.fail(
                                    f"aede/cli.py line {node.lineno}: "
                                    "`return await _run(resume_session_id=...)` is a "
                                    "recursive tail call that grows the async stack unboundedly. "
                                    "Replace with a loop or return the target to the caller. "
                                    "(issue #28)"
                                )
