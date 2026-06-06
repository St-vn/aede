import pytest
from unittest.mock import patch, MagicMock
from aede.cli import build_header, parse_args


def test_build_header_contains_version():
    header = build_header(model="claude-sonnet-4-20250514", session_id="01JABC123")
    assert "v0.1" in header
    assert "claude-sonnet-4-20250514" in header
    assert "01JA" in header  # short ID shown


def test_parse_args_no_task():
    args = parse_args([])
    assert args.task is None


def test_parse_args_with_task():
    args = parse_args(["research pgvector indexing"])
    assert args.task == "research pgvector indexing"


def test_parse_args_version_flag():
    with pytest.raises(SystemExit):
        parse_args(["--version"])
