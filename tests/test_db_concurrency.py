"""Concurrency tests for aede.db.DB — D1 write-lock coverage.

Spawns N threads each performing M write operations on the same DB instance
and asserts that:
  - no exception is raised (no ``database is locked`` / ``ProgrammingError``)
  - the final row counts are exactly correct (no lost writes)

Without the threading.RLock these races / raises intermittently under WAL
with check_same_thread=False.  With the lock the result is deterministic.
"""
from __future__ import annotations

import threading
import uuid
from pathlib import Path

import pytest

from aede.db import DB

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_db(tmp_path: Path) -> DB:
    return DB(tmp_path / "concurrency_test.db")


def _unique() -> str:
    """Return a short random unique string suitable for IDs / content."""
    return uuid.uuid4().hex


# ── test ─────────────────────────────────────────────────────────────────────

def test_concurrent_writes_no_lost_rows(tmp_path: Path) -> None:
    """8 threads × 50 insert_session + insert_message + insert_token_usage.

    Total expected:
      sessions     : 8 × 50 = 400
      messages     : 8 × 50 = 400
      token_usage  : 8 × 50 = 400

    Every write must land exactly once — no lost updates, no exceptions.
    """
    N_THREADS = 8
    WRITES_PER_THREAD = 50

    db = _make_db(tmp_path)
    errors: list[Exception] = []

    def worker() -> None:
        try:
            for _ in range(WRITES_PER_THREAD):
                sid = _unique()
                mid = _unique()
                tid = _unique()
                db.insert_session(
                    id=sid,
                    parent_id=None,
                    title=f"t-{sid}",
                    model="claude-test",
                )
                db.insert_message(
                    id=mid,
                    session_id=sid,
                    role="user",
                    content=f"msg-{mid}",
                    token_count=5,
                )
                db.insert_token_usage(
                    id=tid,
                    session_id=sid,
                    turn_number=1,
                    input_tokens=10,
                    output_tokens=5,
                    cached_tokens=0,
                )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # surface any thread errors as a clear failure message
    assert not errors, f"Thread exceptions: {errors}"

    expected = N_THREADS * WRITES_PER_THREAD

    n_sessions = db.con.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    n_messages = db.con.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
    n_tokens   = db.con.execute("SELECT COUNT(*) AS c FROM token_usage").fetchone()["c"]

    assert n_sessions == expected, f"sessions: expected {expected}, got {n_sessions}"
    assert n_messages == expected, f"messages: expected {expected}, got {n_messages}"
    assert n_tokens   == expected, f"token_usage: expected {expected}, got {n_tokens}"

    db.close()


def test_concurrent_tool_call_writes(tmp_path: Path) -> None:
    """4 threads each insert sessions + messages + tool_calls concurrently."""
    N_THREADS = 4
    WRITES_PER_THREAD = 30

    db = _make_db(tmp_path)
    errors: list[Exception] = []

    # Pre-create one session and one message so tool_calls have valid FKs
    parent_sid = _unique()
    parent_mid = _unique()
    db.insert_session(id=parent_sid, parent_id=None, title="parent", model="m")
    db.insert_message(
        id=parent_mid, session_id=parent_sid, role="user",
        content="seed", token_count=None,
    )

    def worker() -> None:
        try:
            for _ in range(WRITES_PER_THREAD):
                tc_id = _unique()
                db.insert_tool_call(
                    id=tc_id,
                    message_id=parent_mid,
                    tool_name="bash",
                    args="{}",
                    status="running",
                )
                db.update_tool_call(
                    id=tc_id,
                    result="ok",
                    status="done",
                    duration_ms=1,
                )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread exceptions: {errors}"

    expected = N_THREADS * WRITES_PER_THREAD
    n_tc = db.con.execute("SELECT COUNT(*) AS c FROM tool_calls").fetchone()["c"]
    assert n_tc == expected, f"tool_calls: expected {expected}, got {n_tc}"

    db.close()


def test_concurrent_mixed_writers(tmp_path: Path) -> None:
    """Mixed writers: insert_session, insert_message, insert_learning, insert_doc."""
    N_THREADS = 6
    WRITES_PER_THREAD = 25

    db = _make_db(tmp_path)
    errors: list[Exception] = []

    def worker() -> None:
        try:
            for _ in range(WRITES_PER_THREAD):
                sid = _unique()
                db.insert_session(
                    id=sid, parent_id=None,
                    title="mixed", model="m",
                )
                db.insert_message(
                    id=_unique(), session_id=sid,
                    role="assistant", content="hi",
                    token_count=3,
                )
                db.insert_learning(
                    id=_unique(), type="anti-pattern",
                    content="concurrent test", source="test",
                )
                doc_path = f"/docs/{_unique()}.md"
                db.insert_doc(
                    path=doc_path, mtime=0,
                    size=len("hello"), content="hello",
                )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread exceptions: {errors}"

    total = N_THREADS * WRITES_PER_THREAD

    n_s = db.con.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    n_m = db.con.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
    n_l = db.con.execute("SELECT COUNT(*) AS c FROM learnings").fetchone()["c"]
    n_d = db.con.execute("SELECT COUNT(*) AS c FROM docs").fetchone()["c"]

    assert n_s == total, f"sessions: expected {total}, got {n_s}"
    assert n_m == total, f"messages: expected {total}, got {n_m}"
    assert n_l == total, f"learnings: expected {total}, got {n_l}"
    assert n_d == total, f"docs: expected {total}, got {n_d}"

    db.close()
