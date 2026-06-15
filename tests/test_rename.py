import pytest
from unittest.mock import MagicMock
from aede.commands import parse_command
from aede.db import DB
from aede.session import Session


def test_parse_rename():
    result = parse_command("/rename My Session")
    assert result is not None
    assert result.name == "rename"
    assert result.args == ["My", "Session"]


def test_rename_in_commands():
    from aede.commands import COMMANDS
    assert "rename" in COMMANDS


def test_handle_rename_updates_title(tmp_home):
    from aede.commands import handle_rename
    db = DB(tmp_home / "aede.db")
    session = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    console = MagicMock()
    handle_rename(["My New Title"], session, db, console)
    reloaded = Session.load(db, session.id)
    assert reloaded.title == "My New Title"


def test_handle_rename_empty_args_shows_usage(tmp_home):
    from aede.commands import handle_rename
    db = DB(tmp_home / "aede.db")
    session = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    console = MagicMock()
    handle_rename([], session, db, console)
    output = "\n".join(c[0][0] for c in console.print.call_args_list)
    assert "usage" in output.lower() or "Usage" in output
