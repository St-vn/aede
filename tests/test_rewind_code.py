import subprocess
from pathlib import Path
import pytest
from aede.tools.rewind import (
    _try_git_stash_create,
    _try_reverse_replay,
    _sha256,
    revert_code,
)


def test_git_stash_create_restores_workspace(tmp_path):
    """Primary path: git stash-create commits state without touching working tree."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(repo), check=True, capture_output=True)
    f = repo / "a.txt"
    f.write_text("hello")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo), check=True, capture_output=True)
    f.write_text("world")  # changed by agent after rewind point
    result = _try_git_stash_create(repo)
    assert result is True
    assert f.read_text() == "hello"


def test_reverse_replay_restores_file(tmp_path):
    """Fallback path: old_string/new_string replay when no git."""
    f = tmp_path / "x.txt"
    f.write_text("original")
    edits = [{"name": "write_file", "args": {"path": "x.txt", "old_string": "original", "new_string": "changed"}}]
    f.write_text("changed")
    _try_reverse_replay(tmp_path, edits)
    assert f.read_text() == "original"


def test_hash_guard_warns_on_external_edit(tmp_path):
    """Detect file changed outside aede and warn before reverting."""
    f = tmp_path / "x.txt"
    f.write_text("original")
    edits = [{"name": "write_file", "args": {"path": "x.txt", "old_string": "original", "new_string": "changed"}}]
    f.write_text("changed")
    f.write_text("external_edit")  # user changed it externally
    with pytest.warns(UserWarning, match="modified outside aede"):
        _try_reverse_replay(tmp_path, edits)


def test_revert_code_returns_shell_calls(tmp_path):
    """Shell-side-effect tool calls are returned for manual cleanup."""
    tool_calls = [
        {"name": "write_file", "args": {"path": "x.txt", "old_string": "old", "new_string": "new"}},
        {"name": "powershell", "args": {"command": "rm -rf /tmp"}},
    ]
    f = tmp_path / "x.txt"
    f.write_text("new")
    result = revert_code(tmp_path, tool_calls)
    assert len(result) == 1
    assert result[0]["name"] == "powershell"


def test_revert_code_fallback_replay(tmp_path):
    """Without git, revert_code falls back to reverse replay."""
    f = tmp_path / "x.txt"
    f.write_text("original")
    tool_calls = [{"name": "write_file", "args": {"path": "x.txt", "old_string": "original", "new_string": "changed"}}]
    f.write_text("changed")
    revert_code(tmp_path, tool_calls)
    assert f.read_text() == "original"


def test_reverse_replay_unlinks_created_file(tmp_path):
    """create_file is undone by unlinking the file."""
    f = tmp_path / "new.txt"
    f.write_text("hello")
    edits = [{"name": "create_file", "args": {"path": "new.txt", "content": "hello"}}]
    _try_reverse_replay(tmp_path, edits)
    assert not f.exists()
