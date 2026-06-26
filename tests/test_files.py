from __future__ import annotations
from pathlib import Path
import sys
import os

import pytest


def test_edit_outside_fileset_rejected():
    """RED 1: edit on path outside fileset is rejected."""
    from aede.tools.files import edit
    from aede.sandboxing.fileset import FileSet

    fs = FileSet(declared={"/workspace/src"}, session_id="test")
    result = edit(
        {"path": "/etc/passwd", "old_string": "root", "new_string": "admin"},
        fileset=fs,
    )
    assert "outside declared fileset" in result


def test_read_file_outside_fileset_rejected():
    """read_file on path outside fileset is rejected."""
    from aede.tools.files import read_file
    from aede.sandboxing.fileset import FileSet

    fs = FileSet(declared={"/workspace/src"}, session_id="test")
    result = read_file({"path": "/etc/passwd"}, fileset=fs)
    assert "outside declared fileset" in result


@pytest.mark.skipif(sys.platform == "win32", reason="symlink requires admin/Developer Mode on Windows")
def test_read_file_symlink_outside_not_followed(tmp_path: Path):
    """RED 2: symlink whose target is outside scope is NOT followed."""
    from aede.tools.files import read_file
    from aede.sandboxing.fileset import FileSet

    allowed = tmp_path / "project"
    allowed.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret-data")
    link = allowed / "evil_link.txt"
    link.symlink_to(outside)

    fs = FileSet(declared={str(allowed)}, session_id="test")
    result = read_file({"path": str(link)}, fileset=fs)
    assert "outside declared fileset" in result


@pytest.mark.skipif(sys.platform == "win32", reason="symlink requires admin/Developer Mode on Windows")
def test_edit_resolves_before_exists_check(tmp_path: Path):
    """edit resolves path before checking exists()."""
    from aede.tools.files import edit
    from aede.sandboxing.fileset import FileSet

    allowed = tmp_path / "project"
    allowed.mkdir()
    target = allowed / "target.txt"
    target.write_text("hello world")
    working = tmp_path / "working"
    working.mkdir()
    link = working / "link.txt"
    link.symlink_to(target)

    fs = FileSet(declared={str(allowed)}, session_id="test")
    result = edit(
        {"path": str(link), "old_string": "hello", "new_string": "hi"},
        fileset=fs,
    )
    assert "outside declared fileset" in result


def test_glob_files_max_depth(tmp_path: Path):
    """RED 3: deep directory tree is capped at max_depth."""
    from aede.tools.files import glob_files

    d = tmp_path
    for i in range(15):
        d = d / f"sub{i}"
        d.mkdir()

    deep_file = d / "found.txt"
    deep_file.write_text("deep")

    shallow = tmp_path / "sub0" / "shallow.txt"
    shallow.write_text("shallow")

    result = glob_files({"pattern": "found.txt", "path": str(tmp_path)})
    assert "found.txt" not in result, "deeply nested file past max_depth was found"

    result2 = glob_files({"pattern": "shallow.txt", "path": str(tmp_path)})
    assert "shallow.txt" in result2, "shallow file within max_depth should be found"


def test_glob_files_max_results(tmp_path: Path):
    """glob_files caps at max_results."""
    from aede.tools.files import glob_files

    for i in range(100):
        f = tmp_path / f"file{i}.txt"
        f.write_text(f"content{i}")

    result = glob_files({"pattern": "*.txt", "path": str(tmp_path)})
    lines = [l for l in result.splitlines() if l and not l.startswith("[truncated")]
    assert 0 < len(lines) <= 5000
    assert len(lines) <= 100


def test_read_file_inside_fileset_works(tmp_path: Path):
    """Positive: legit read inside fileset works."""
    from aede.tools.files import read_file
    from aede.sandboxing.fileset import FileSet

    allowed = tmp_path / "project"
    allowed.mkdir()
    f = allowed / "hello.txt"
    f.write_text("hello world")

    fs = FileSet(declared={str(allowed)}, session_id="test")
    result = read_file({"path": str(f)}, fileset=fs)
    assert "hello world" in result


def test_edit_inside_fileset_works(tmp_path: Path):
    """Positive: legit edit inside fileset works."""
    from aede.tools.files import edit
    from aede.sandboxing.fileset import FileSet

    allowed = tmp_path / "project"
    allowed.mkdir()
    f = allowed / "hello.txt"
    f.write_text("hello world")

    fs = FileSet(declared={str(allowed)}, session_id="test")
    result = edit({"path": str(f), "old_string": "hello", "new_string": "hi"}, fileset=fs)
    assert "Edited" in result
    assert f.read_text() == "hi world"


def test_glob_files_positive(tmp_path: Path):
    """Positive: glob finds matching files."""
    from aede.tools.files import glob_files

    (tmp_path / "alpha.py").write_text("a")
    (tmp_path / "beta.py").write_text("b")
    (tmp_path / "gamma.txt").write_text("c")

    result = glob_files({"pattern": "*.py", "path": str(tmp_path)})
    assert "alpha.py" in result
    assert "beta.py" in result
    assert "gamma.txt" not in result


@pytest.mark.skipif(sys.platform == "win32", reason="symlink requires admin/Developer Mode on Windows")
def test_read_file_symlink_allowed_when_target_inside(tmp_path: Path):
    """Positive: symlink to an inside-target is followed."""
    from aede.tools.files import read_file
    from aede.sandboxing.fileset import FileSet

    allowed = tmp_path / "project"
    allowed.mkdir()
    target = allowed / "real.txt"
    target.write_text("accessible")
    link = allowed / "link.txt"
    link.symlink_to(target)

    fs = FileSet(declared={str(allowed)}, session_id="test")
    result = read_file({"path": str(link)}, fileset=fs)
    assert "accessible" in result
