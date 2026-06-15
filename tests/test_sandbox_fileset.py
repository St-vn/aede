from __future__ import annotations
from pathlib import Path
import pytest


def test_fileset_default_deny():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    assert fs.allowed("/some/random/path") is False


def test_fileset_allow_path():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    fs.allow(Path("/workspace/src/main.py"))
    assert fs.allowed("/workspace/src/main.py") is True


def test_fileset_allow_directory():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    fs.allow(Path("/workspace/src"))
    assert fs.allowed("/workspace/src/main.py") is True
    assert fs.allowed("/workspace/src/utils/helper.py") is True


def test_fileset_deny_outside_declared():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    fs.allow(Path("/workspace/src"))
    assert fs.allowed("/etc/passwd") is False
    assert fs.allowed("/workspace/other/file.txt") is False


def test_fileset_declare_from_prompt_infers_paths():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    fs.declare_from_prompt("Fix the bug in src/main.py and update tests/test_main.py")
    assert fs.allowed("src/main.py") is True
    assert fs.allowed("tests/test_main.py") is True
    assert fs.allowed("/etc/hosts") is False


def test_fileset_reset_clears_allowed():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    fs.allow(Path("/workspace/src"))
    fs.reset()
    assert fs.allowed("/workspace/src/main.py") is False


def test_fileset_declared_set_readonly():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    paths = fs.declared_set()
    assert isinstance(paths, set)


def test_fileset_declare_auto_workspace():
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    workspace = Path("/workspace")
    fs.declare_workspace(workspace)
    assert fs.allowed("/workspace/src/main.py") is True
    assert fs.allowed("/workspace") is True


import sys


@pytest.mark.skipif(sys.platform == "win32", reason="symlink requires admin on Windows")
def test_fileset_deny_symlink_escape(tmp_path):
    from aede.sandboxing.fileset import FileSet
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    link = tmp_path / "link"
    link.symlink_to(outside)
    fs = FileSet()
    fs.allow(tmp_path / "data")
    assert fs.allowed(str(link)) is False


def test_fileset_allowed_paths_list(tmp_path):
    from aede.sandboxing.fileset import FileSet
    fs = FileSet()
    a = tmp_path / "a"
    b = tmp_path / "b"
    fs.allow(a)
    fs.allow(b)
    allowed = fs.allowed_paths()
    assert a.resolve() in allowed
    assert b.resolve() in allowed
