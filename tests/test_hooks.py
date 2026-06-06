import pytest
from aede.hooks import pre_tool_use, HardDeniedError


def test_safe_command_passes():
    pre_tool_use("powershell", {"cmd": "pytest tests/"})


def test_rm_rf_root_denied():
    with pytest.raises(HardDeniedError, match="rm -rf /"):
        pre_tool_use("powershell", {"cmd": "rm -rf /"})


def test_windows_root_delete_denied():
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "del /f /s /q C:\\"})


def test_format_drive_denied():
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "format C:"})


def test_rd_root_denied():
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "rd /s /q C:\\"})


def test_fork_bomb_denied():
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": ":(){ :|:& };"})


def test_shutdown_denied():
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "shutdown /s /t 0"})


def test_non_shell_tool_passes():
    pre_tool_use("read_file", {"path": "/some/path"})
    pre_tool_use("web_search", {"query": "test"})


def test_rm_rf_subdir_passes():
    pre_tool_use("powershell", {"cmd": "rm -rf ./dist"})
