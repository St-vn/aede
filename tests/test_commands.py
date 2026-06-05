import pytest
from unittest.mock import MagicMock
from jarvis.commands import parse_command, CommandResult, COMMANDS


def test_parse_help():
    result = parse_command("/help")
    assert result.name == "help"
    assert result.args == []


def test_parse_resume_no_args():
    result = parse_command("/resume")
    assert result.name == "resume"
    assert result.args == []


def test_parse_resume_with_id():
    result = parse_command("/resume 01J000ABC")
    assert result.name == "resume"
    assert result.args == ["01J000ABC"]


def test_parse_config_no_args():
    result = parse_command("/config")
    assert result.name == "config"
    assert result.args == []


def test_parse_config_with_scope():
    result = parse_command("/config global model claude-opus-4")
    assert result.name == "config"
    assert result.args == ["global", "model", "claude-opus-4"]


def test_parse_tokens():
    result = parse_command("/tokens")
    assert result.name == "tokens"


def test_parse_exit():
    result = parse_command("/exit")
    assert result.name == "exit"


def test_parse_clear():
    result = parse_command("/clear")
    assert result.name == "clear"


def test_parse_compact():
    result = parse_command("/compact")
    assert result.name == "compact"


def test_parse_sessions():
    result = parse_command("/sessions")
    assert result.name == "sessions"


def test_parse_tools():
    result = parse_command("/tools")
    assert result.name == "tools"


def test_parse_unknown_returns_none():
    result = parse_command("/unknown_command")
    assert result is None


def test_all_commands_registered():
    for name in ["help", "resume", "sessions", "tools", "config", "compact", "tokens", "clear", "exit"]:
        assert name in COMMANDS
