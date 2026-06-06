import pytest
from aede.session import generate_session_id, make_title, Session
from aede.db import DB


def test_generate_session_id_is_ulid():
    from ulid import ULID
    sid = generate_session_id()
    ULID.from_str(sid)


def test_generate_session_id_sortable():
    import time
    id1 = generate_session_id()
    time.sleep(0.001)
    id2 = generate_session_id()
    assert id1 < id2


def test_make_title_truncates():
    long_msg = "a" * 100
    title = make_title(long_msg)
    assert len(title) <= 60


def test_make_title_short_message():
    title = make_title("hi")
    assert "hi" in title
    assert "·" in title  # timestamp appended


def test_make_title_normal():
    title = make_title("debug session restore function in harness")
    assert title == "debug session restore function in harness"


def test_session_create_and_get(tmp_home):
    db = DB(tmp_home / "aede.db")
    s = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    assert s.id is not None
    loaded = Session.load(db=db, session_id=s.id)
    assert loaded.id == s.id
    assert loaded.status == "active"


def test_session_branch(tmp_home):
    db = DB(tmp_home / "aede.db")
    parent = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    branch = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=parent.id)
    assert branch.parent_id == parent.id
    loaded_parent = Session.load(db=db, session_id=parent.id)
    assert loaded_parent.id == parent.id


def test_session_list(tmp_home):
    db = DB(tmp_home / "aede.db")
    for i in range(3):
        Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    sessions = Session.list_recent(db=db, limit=10)
    assert len(sessions) == 3
