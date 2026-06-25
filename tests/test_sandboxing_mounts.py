import pytest
import sys
from pathlib import Path


def test_host_to_container_path_unc():
    from aede.sandboxing.mounts import _host_to_container_path

    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    with pytest.raises(ValueError, match="UNC"):
        _host_to_container_path(Path("\\\\server\\share\\dir"))


def test_host_to_container_path_too_short():
    from aede.sandboxing.mounts import _host_to_container_path

    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    with pytest.raises(ValueError, match="too short"):
        _host_to_container_path(Path("x"))
