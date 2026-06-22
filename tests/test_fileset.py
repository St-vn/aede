from __future__ import annotations
from pathlib import Path
import sys

import pytest


def test_is_writable_inside_declared_directory():
    from aede.sandboxing.fileset import FileSet

    fs = FileSet(declared={"/workspace/src"}, session_id="test-session")
    assert fs.is_writable("/workspace/src/main.py") is True
    assert fs.is_writable("/workspace/src/utils/helper.py") is True


def test_is_writable_outside_declared_set():
    from aede.sandboxing.fileset import FileSet

    fs = FileSet(declared={"/workspace/src"}, session_id="test-session")
    assert fs.is_writable("/etc/passwd") is False
    assert fs.is_writable("/workspace/docs/readme.md") is False


@pytest.mark.skipif(sys.platform == "win32", reason="symlink requires admin/Developer Mode on Windows")
def test_is_writable_symlink_resolution(tmp_path: Path):
    from aede.sandboxing.fileset import FileSet

    declared_dir = tmp_path / "project" / "src"
    declared_dir.mkdir(parents=True)

    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret")

    link = declared_dir / "evil_link.txt"
    link.symlink_to(outside_file)

    fs = FileSet(declared={str(declared_dir)}, session_id="test-session")
    resolved = str(link.resolve())
    assert resolved not in fs.declared
    assert fs.is_writable(str(link)) is False


def test_is_writable_respects_path_boundary():
    from aede.sandboxing.fileset import FileSet

    # Declared path that could be a prefix of a completely different path
    fs = FileSet(declared={"/workspace/src"}, session_id="test-session")
    # "/workspace/src-backup" starts with "/workspace/src" but is a different directory
    assert fs.is_writable("/workspace/src-backup/file.txt") is False


def test_declare_fileset_creates_explicit():
    from aede.sandboxing.fileset import FileSet, declare_fileset

    current = FileSet(declared={"/old/path"}, session_id="test-session")
    result = declare_fileset(["/workspace/src", "/workspace/tests"], "auth refactor", current)

    assert result.source == "explicit"
    assert result.session_id == "test-session"
    assert result.inferred_from_prompt == "auth refactor"
    assert len(result.declared) == 2
    expected = {str(Path(p).resolve()) for p in ["/workspace/src", "/workspace/tests"]}
    assert result.declared == expected


def test_infer_fileset_creates_inferred(tmp_path: Path):
    from aede.sandboxing.fileset import infer_fileset

    fs = infer_fileset(tmp_path, "test-session")
    assert fs.source == "inferred"
    assert fs.session_id == "test-session"
    assert str(tmp_path.resolve()) in fs.declared


def test_multiple_declared_paths_all_work():
    from aede.sandboxing.fileset import FileSet

    fs = FileSet(
        declared={"/workspace/src", "/workspace/docs", "/workspace/tests"},
        session_id="test-session",
    )
    assert fs.is_writable("/workspace/src/main.py") is True
    assert fs.is_writable("/workspace/docs/README.md") is True
    assert fs.is_writable("/workspace/tests/test_main.py") is True
    assert fs.is_writable("/workspace/.env") is False
