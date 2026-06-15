import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from aede.cli import parse_args


def test_parse_args_daemon_start():
    args = parse_args(["daemon", "start"])
    assert args.command == "daemon"
    assert args.daemon_subcommand == "start"


def test_parse_args_daemon_stop():
    args = parse_args(["daemon", "stop"])
    assert args.command == "daemon"
    assert args.daemon_subcommand == "stop"


def test_parse_args_daemon_status():
    args = parse_args(["daemon", "status"])
    assert args.command == "daemon"
    assert args.daemon_subcommand == "status"


def test_parse_args_attach():
    args = parse_args(["--attach"])
    assert args.attach is True


def test_parse_args_attach_with_task():
    args = parse_args(["--attach", "hello world"])
    assert args.attach is True
    assert args.task == "hello world"


def test_parse_args_daemon_unknown_subcommand_raises():
    with pytest.raises(SystemExit):
        parse_args(["daemon", "fly"])


def test_parse_args_daemon_without_subcommand():
    args = parse_args(["daemon"])
    assert args.command == "daemon"
    assert getattr(args, "daemon_subcommand", None) is None



