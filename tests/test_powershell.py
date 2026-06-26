import shutil
import pytest
import subprocess
from unittest.mock import MagicMock, patch
from aede.tools.powershell import run_powershell

# These tests spawn the real `powershell` binary, which only exists on Windows
# (and PowerShell-Core installs). Skip where it isn't available (e.g. Linux CI).
pytestmark = pytest.mark.skipif(
    shutil.which("powershell") is None and shutil.which("pwsh") is None,
    reason="powershell binary not available on this platform",
)


def test_callback_exception_reaps_process():
    popen_instances = []
    original_popen = subprocess.Popen

    def tracking_popen(*a, **kw):
        inst = original_popen(*a, **kw)
        popen_instances.append(inst)
        return inst

    with patch("aede.tools.powershell.subprocess.Popen", tracking_popen):
        args = {"cmd": "echo hello; Start-Sleep 10"}
        callback = MagicMock(side_effect=ValueError("boom"))
        with pytest.raises(ValueError, match="boom"):
            run_powershell(args, stream_callback=callback)

    assert len(popen_instances) == 1
    assert popen_instances[0].poll() is not None


def test_output_exceeds_limit():
    with patch("aede.tools.powershell._MAX_OUTPUT_BYTES", 100):
        args = {"cmd": "python -c \"import sys; sys.stdout.write('x' * 200)\""}
        with pytest.raises(RuntimeError, match="10 MiB"):
            run_powershell(args)
