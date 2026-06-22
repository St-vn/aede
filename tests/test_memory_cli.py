"""
Tests for `aede memory` CLI subcommand — T-05 (list / show / delete / edit).

TDD: these tests are written FIRST and must fail before implementation.
"""
from __future__ import annotations
import json
import os
import sys
import textwrap
import pytest
from pathlib import Path
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _store(tmp_home):
    """Return a LearningsStore backed by tmp_home."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore

    bootstrap(tmp_home)
    return LearningsStore(tmp_home / "data")


def _invoke_memory_cli(argv: list[str], tmp_home: Path) -> str:
    """
    Call the memory CLI path synchronously.

    We import `main_memory` (or route via parse_args) directly to avoid
    spawning a subprocess and hanging on the REPL.
    """
    from aede.cli import run_memory_command
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        run_memory_command(argv, tmp_home)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# T-05a: list
# ---------------------------------------------------------------------------


def test_memory_list_empty(tmp_home):
    """aede memory list on empty store prints no error and 0 entries."""
    from aede.config import bootstrap
    bootstrap(tmp_home)
    out = _invoke_memory_cli(["list"], tmp_home)
    # Should succeed (not raise) and indicate empty state
    assert isinstance(out, str)


def test_memory_list_shows_entries(tmp_home):
    """aede memory list shows id, type, and truncated content for each entry."""
    store = _store(tmp_home)
    store.write_learning(
        type="anti-pattern",
        content="Never concatenate SQL strings directly.",
        source="user",
        source_session_id="S1",
    )
    store.write_learning(
        type="root-cause",
        content="The crash is due to a null pointer dereference.",
        source="test_failure",
        source_session_id="S2",
    )

    out = _invoke_memory_cli(["list"], tmp_home)

    assert "anti-pattern" in out
    assert "root-cause" in out
    # Content should appear (possibly truncated)
    assert "Never concatenate" in out or "Never" in out


# ---------------------------------------------------------------------------
# T-05b: show
# ---------------------------------------------------------------------------


def test_memory_show_full(tmp_home):
    """aede memory show <id> prints the full JSON record."""
    store = _store(tmp_home)
    store.write_learning(
        type="failed-approach",
        content="Tried using X but it failed because of Y.",
        source="auto_learned",
        source_session_id="S3",
    )

    # Get the ID from the JSONL
    jsonl = (tmp_home / "data" / "learnings.jsonl").read_text(encoding="utf-8")
    record = json.loads(jsonl.strip().splitlines()[0])
    learning_id = record["id"]

    out = _invoke_memory_cli(["show", learning_id], tmp_home)

    assert "failed-approach" in out
    assert "Tried using X" in out
    assert learning_id in out


def test_memory_show_unknown_id(tmp_home):
    """aede memory show with unknown id prints an error."""
    from aede.config import bootstrap
    bootstrap(tmp_home)
    out = _invoke_memory_cli(["show", "NONEXISTENTID"], tmp_home)
    assert "not found" in out.lower() or "error" in out.lower() or "NONEXISTENTID" in out


# ---------------------------------------------------------------------------
# T-05c: delete
# ---------------------------------------------------------------------------


def test_memory_delete_removes_entry(tmp_home):
    """aede memory delete <id> removes the entry from the JSONL file."""
    store = _store(tmp_home)
    store.write_learning(
        type="config-correction",
        content="Setting X=5 not X=50.",
        source="user",
        source_session_id="S4",
    )
    store.write_learning(
        type="anti-pattern",
        content="Do not use raw threads.",
        source="user",
        source_session_id="S5",
    )

    jsonl_path = tmp_home / "data" / "learnings.jsonl"
    lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2

    first_id = json.loads(lines[0])["id"]

    _invoke_memory_cli(["delete", first_id], tmp_home)

    lines_after = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines_after) == 1, f"Expected 1 line after delete, got {len(lines_after)}"

    remaining = json.loads(lines_after[0])
    assert remaining["id"] != first_id


def test_memory_delete_unknown_id_is_noop(tmp_home):
    """Deleting a non-existent id should not raise — it's a no-op."""
    from aede.config import bootstrap
    bootstrap(tmp_home)
    # Should not raise
    _invoke_memory_cli(["delete", "FAKEID"], tmp_home)


# ---------------------------------------------------------------------------
# T-05d: edit (with mocked editor)
# ---------------------------------------------------------------------------


def test_memory_edit_applies_mutation(tmp_home, monkeypatch):
    """aede memory edit <id> opens editor on temp file; edited JSON is written back."""
    store = _store(tmp_home)
    store.write_learning(
        type="anti-pattern",
        content="Original content.",
        source="user",
        source_session_id="S6",
    )

    jsonl_path = tmp_home / "data" / "learnings.jsonl"
    lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    record = json.loads(lines[0])
    learning_id = record["id"]

    # Mock subprocess.run to simulate an editor that changes 'content'
    def fake_editor(cmd, **kwargs):
        # cmd is [editor_binary, tmp_file_path]
        tmp_file = Path(cmd[-1])
        data = json.loads(tmp_file.read_text(encoding="utf-8"))
        data["content"] = "Edited content."
        tmp_file.write_text(json.dumps(data), encoding="utf-8")

    import subprocess
    monkeypatch.setattr(subprocess, "run", fake_editor)
    monkeypatch.setenv("EDITOR", "fake-editor")

    _invoke_memory_cli(["edit", learning_id], tmp_home)

    lines_after = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines_after) == 1
    updated = json.loads(lines_after[0])
    assert updated["content"] == "Edited content.", f"Content not updated: {updated}"
    assert updated["id"] == learning_id


def test_memory_edit_rejects_invalid_json(tmp_home, monkeypatch):
    """aede memory edit must reject a temp file with broken JSON (validate before save)."""
    store = _store(tmp_home)
    store.write_learning(
        type="anti-pattern",
        content="Original.",
        source="user",
        source_session_id="S7",
    )

    jsonl_path = tmp_home / "data" / "learnings.jsonl"
    lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    record = json.loads(lines[0])
    learning_id = record["id"]

    def bad_editor(cmd, **kwargs):
        tmp_file = Path(cmd[-1])
        tmp_file.write_text("this is not valid json!!!", encoding="utf-8")

    import subprocess
    monkeypatch.setattr(subprocess, "run", bad_editor)
    monkeypatch.setenv("EDITOR", "fake-editor")

    # Should not crash; should print an error instead of saving bad data
    out = _invoke_memory_cli(["edit", learning_id], tmp_home)
    # Original should be unchanged
    lines_after = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    original = json.loads(lines_after[0])
    assert original["content"] == "Original.", "Original content should be preserved after bad edit"


# ---------------------------------------------------------------------------
# T-05e: parse_args still works for normal task path after subparser addition
# ---------------------------------------------------------------------------


def test_parse_args_task_still_works():
    """Adding memory subcommands must not break `aede 'do a task'` parsing."""
    from aede.cli import parse_args

    args = parse_args(["do something useful"])
    # Must not be interpreted as a memory subcommand
    assert getattr(args, "command", None) != "memory"
    assert args.task == "do something useful"


def test_parse_args_memory_list():
    """parse_args recognises `aede memory list`."""
    from aede.cli import parse_args

    args = parse_args(["memory", "list"])
    assert args.command == "memory"
    assert args.memory_subcommand == "list"


def test_parse_args_memory_show():
    """parse_args recognises `aede memory show <id>`."""
    from aede.cli import parse_args

    args = parse_args(["memory", "show", "SOMEID"])
    assert args.command == "memory"
    assert args.memory_subcommand == "show"
    assert args.id == "SOMEID"


def test_parse_args_memory_delete():
    """parse_args recognises `aede memory delete <id>`."""
    from aede.cli import parse_args

    args = parse_args(["memory", "delete", "SOMEID"])
    assert args.command == "memory"
    assert args.memory_subcommand == "delete"
    assert args.id == "SOMEID"


def test_parse_args_memory_edit():
    """parse_args recognises `aede memory edit <id>`."""
    from aede.cli import parse_args

    args = parse_args(["memory", "edit", "SOMEID"])
    assert args.command == "memory"
    assert args.memory_subcommand == "edit"
    assert args.id == "SOMEID"


def test_parse_args_no_task_still_works():
    """parse_args [] still returns task=None (REPL launch path)."""
    from aede.cli import parse_args

    args = parse_args([])
    assert getattr(args, "command", None) is None or args.command != "memory"
    assert args.task is None
