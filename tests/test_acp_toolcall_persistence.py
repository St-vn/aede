# tests/test_acp_toolcall_persistence.py
"""Regression tests for the two ACP/claude-code tool-call UI bugs:

1. Tool-call cards disappeared after streaming for ACP (claude-code) turns,
   because ACP agents report tool calls *during* the provider call — before
   _current_assist_id was set and before the assistant message row existed —
   so the persist callback's FK target was missing and the call was never
   written.  On the post-turn refetch the card vanished.  Fixed by inserting
   the assistant row + setting _current_assist_id BEFORE the provider call.

2. Native write_file/create_file showed a raw JSON block instead of the inline
   diff that ACP "Edit" gets, because the UI keys the diff renderer off
   old_string/new_string which native tools don't carry.  Fixed by
   _enrich_edit_args attaching that pair (reading old content pre-write).
"""
from pathlib import Path

from aede.agent import AgentLoop
from aede.db import DB


def _bare_loop(db: DB) -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop._db = db
    loop._current_assist_id = None
    loop._stream_tool_call = None
    return loop


# ── Bug 2: edit-arg enrichment ──────────────────────────────────────


def test_enrich_write_file_adds_old_new(tmp_path):
    loop = _bare_loop(db=None)  # _enrich_edit_args only touches the filesystem
    f = tmp_path / "f.txt"
    f.write_text("hello world\n", encoding="utf-8")
    args = {"path": str(f), "content": "goodbye world\n"}
    out = loop._enrich_edit_args("write_file", args)
    assert out["old_string"] == "hello world\n"
    assert out["new_string"] == "goodbye world\n"
    # Original dict is not mutated (it still feeds tool execution + trace).
    assert "old_string" not in args


def test_enrich_create_file_old_is_empty(tmp_path):
    loop = _bare_loop(db=None)
    args = {"path": str(tmp_path / "new.txt"), "content": "fresh\n"}
    out = loop._enrich_edit_args("create_file", args)
    assert out["old_string"] == ""
    assert out["new_string"] == "fresh\n"


def test_enrich_write_file_missing_file_old_empty(tmp_path):
    loop = _bare_loop(db=None)
    args = {"path": str(tmp_path / "absent.txt"), "content": "x\n"}
    out = loop._enrich_edit_args("write_file", args)
    assert out["old_string"] == ""
    assert out["new_string"] == "x\n"


def test_enrich_noop_for_other_tools():
    loop = _bare_loop(db=None)
    args = {"path": "p", "content": "c"}
    assert loop._enrich_edit_args("read_file", args) is args


# ── Bug 1: tool calls persist against a pre-allocated assistant row ──


def test_tool_call_persists_when_assist_id_preset(tmp_path):
    """With _current_assist_id set and the message row inserted (the new
    ordering), _emit_tool_call writes the tool call to the DB so it survives
    the post-turn refetch."""
    db = DB(tmp_path / "t.db")
    from aede.session import Session
    s = Session.create(db, "code/haiku-4", parent_id=None)

    loop = _bare_loop(db)
    loop._session = s

    # Simulate run_turn's new pre-allocation: assist row exists + id set
    # BEFORE any tool call is emitted (as ACP would emit mid-stream).
    from ulid import ULID
    assist_id = str(ULID())
    loop._current_assist_id = assist_id
    db.insert_message(
        id=assist_id, session_id=s.id, role="assistant",
        content="", token_count=None,
    )

    loop._emit_tool_call("call-1", "write_file", {"path": "f", "content": "x"})

    tc = db.get_tool_calls_for_message_ids([assist_id])
    assert assist_id in tc
    assert tc[assist_id][0]["tool_name"] == "write_file"


def test_delete_message_removes_tool_calls(tmp_path):
    """The error-path cleanup drops the empty placeholder and its tool calls."""
    db = DB(tmp_path / "t.db")
    from aede.session import Session
    from ulid import ULID
    s = Session.create(db, "code/haiku-4", parent_id=None)
    assist_id = str(ULID())
    db.insert_message(id=assist_id, session_id=s.id, role="assistant",
                      content="", token_count=None)
    db.upsert_tool_call(id="c1", message_id=assist_id, tool_name="write_file",
                        args="{}", status="running")

    db.delete_message(assist_id)

    assert db.get_tool_calls_for_message_ids([assist_id]) == {}
    assert all(m["id"] != assist_id for m in db.get_messages(s.id))


def test_update_message_finalizes_content(tmp_path):
    db = DB(tmp_path / "t.db")
    from aede.session import Session
    from ulid import ULID
    s = Session.create(db, "code/haiku-4", parent_id=None)
    mid = str(ULID())
    db.insert_message(id=mid, session_id=s.id, role="assistant",
                      content="", token_count=None)
    db.update_message(id=mid, content="final text", token_count=42,
                      thinking="thought")
    row = next(m for m in db.get_messages(s.id) if m["id"] == mid)
    assert row["content"] == "final text"
    assert row["token_count"] == 42
    assert row["thinking"] == "thought"
