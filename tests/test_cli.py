import pytest
from pathlib import Path
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


def test_maybe_set_title_sets_once(tmp_home):
    from aede.cli import _maybe_set_title
    from aede.db import DB
    from aede.session import Session

    db = DB(tmp_home / "aede.db")
    session = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    assert session.title == ""

    # First turn sets title
    _maybe_set_title(session, db, "this is a very long title that should be shortened to make a title")
    assert session.title != ""

    first_title = session.title

    # Second turn must NOT overwrite it
    _maybe_set_title(session, db, "something else entirely")
    assert session.title == first_title


def test_parse_args_import_flag():
    """--import claude-code requires --src."""
    args = parse_args(["--import", "claude-code", "--src", "agent.md"])
    assert args.import_action == "claude-code"
    assert args.src == Path("agent.md")


def test_config_show_mcp_server_count():
    """handle_config_show includes mcp_servers count."""
    from aede.commands import handle_config_show
    from unittest.mock import MagicMock

    cfg = MagicMock()
    cfg.model = "test"
    cfg.compaction_threshold = 0.8
    cfg.tool_output_max_tokens = 500
    cfg.shell = "powershell"
    cfg.batch_approval_max = 5
    cfg.gate_mode = "normal"
    cfg.auto_approve = []
    cfg.sources = {"model": "default"}
    cfg.mcp_servers = {"s1": MagicMock(), "s2": MagicMock()}

    console = MagicMock()
    handle_config_show(cfg, console)
    output = console.print.call_args[0][0]
    assert "2 configured" in output or "mcp_servers" in output


def test_shutdown_prunes_empty_session(tmp_path):
    from aede.cli import _shutdown
    from aede.db import DB
    from aede.session import Session
    from aede.rollout import Rollout

    db_path = tmp_path / "aede.db"
    db = DB(db_path)

    session = Session.create(db, "gpt-4o", None)
    session_id = session.id

    sessions_dir = tmp_path / "sessions"
    rollout = Rollout(sessions_dir, session_id)
    rollout.write({"type": "session_start", "session_id": session_id})
    rollout_path = rollout._path

    assert rollout_path.exists()
    assert db.get_session(session_id) is not None

    # Shutdown with no messages
    _shutdown(session, db, rollout, "exit")

    # Re-open DB
    db = DB(db_path)
    assert db.get_session(session_id) is None
    assert not rollout_path.exists()


def test_shutdown_keeps_session_with_messages(tmp_path):
    from aede.cli import _shutdown
    from aede.db import DB
    from aede.session import Session
    from aede.rollout import Rollout

    db_path = tmp_path / "aede.db"
    db = DB(db_path)

    session = Session.create(db, "gpt-4o", None)
    session_id = session.id

    sessions_dir = tmp_path / "sessions"
    rollout = Rollout(sessions_dir, session_id)
    rollout.write({"type": "session_start", "session_id": session_id})
    rollout_path = rollout._path

    db.insert_message("msg1", session_id, "user", "hello", 10)

    # Shutdown with messages
    _shutdown(session, db, rollout, "exit")

    # Re-open DB
    db = DB(db_path)
    assert db.get_session(session_id) is not None
    assert rollout_path.exists()
