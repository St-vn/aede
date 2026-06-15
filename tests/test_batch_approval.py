import pytest
from unittest.mock import MagicMock
from aede.commands import parse_command


def test_parse_approve():
    result = parse_command("/approve")
    assert result is not None
    assert result.name == "approve"


def test_parse_approve_with_tool():
    result = parse_command("/approve write_file")
    assert result.name == "approve"
    assert result.args == ["write_file"]


def test_parse_approve_multiple():
    result = parse_command("/approve write_file create_file powershell")
    assert result.name == "approve"
    assert result.args == ["write_file", "create_file", "powershell"]


def test_approve_in_commands():
    from aede.commands import COMMANDS
    assert "approve" in COMMANDS


def test_handle_approve_no_args_shows_gated():
    from aede.commands import handle_approve
    router = MagicMock()
    router.tool_names.return_value = ["powershell", "read_file", "write_file"]
    router._session_auto_approve = set()
    gate_store = MagicMock()
    gate_store.list_approved.return_value = []
    console = MagicMock()
    handle_approve([], router, gate_store, console)
    output = "\n".join(c[0][0] for c in console.print.call_args_list)
    assert "powershell" in output
    assert "write_file" in output


def test_handle_approve_with_tools_approves():
    from aede.commands import handle_approve
    router = MagicMock()
    router._session_auto_approve = set()
    gate_store = MagicMock()
    console = MagicMock()
    handle_approve(["powershell", "write_file"], router, gate_store, console)
    router.set_auto_approved.assert_called_once()
    args = router.set_auto_approved.call_args[0][0]
    assert "powershell" in args
    assert "write_file" in args
