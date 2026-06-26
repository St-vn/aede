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


# ---------------------------------------------------------------------------
# H1 — unified blocklist regression
# ---------------------------------------------------------------------------

def test_hooks_hard_deny_git_push_force():
    """H1: hooks must hard-deny git push --force (was missing before unification)."""
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "git push --force"})


def test_hooks_hard_deny_git_push_dash_f():
    """H1: hooks must hard-deny git push -f."""
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "git push -f"})


def test_hooks_hard_deny_git_push_origin_main():
    """H1: hooks must hard-deny git push origin main."""
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "git push origin main"})


def test_hooks_hard_deny_git_push_origin_master():
    """H1: hooks must hard-deny git push origin master."""
    with pytest.raises(HardDeniedError):
        pre_tool_use("powershell", {"cmd": "git push origin master"})


def test_hooks_dangerous_shell_patterns_exported():
    """H1: DANGEROUS_SHELL_PATTERNS must be importable from hooks."""
    from aede.hooks import DANGEROUS_SHELL_PATTERNS
    assert isinstance(DANGEROUS_SHELL_PATTERNS, list)
    assert len(DANGEROUS_SHELL_PATTERNS) >= 12  # union of both old lists
