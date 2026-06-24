"""Tests for LearningsStore -- streaming list_all and concurrent-write safety."""
from __future__ import annotations
import json
import threading


def test_list_all_returns_all_records(tmp_home):
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore
    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")
    ids = []
    for i in range(5):
        r = store.write_learning(
            type="anti-pattern", content=f"Rec {i}", source="user", source_session_id="S",
        )
        ids.append(r["id"])
    all_records = store.list_all()
    assert len(all_records) == 5
    assert [r["id"] for r in all_records] == ids


def test_list_all_empty_file(tmp_home):
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore
    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")
    assert store.list_all() == []


def test_list_all_skips_malformed_lines(tmp_home):
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore
    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")
    jp = tmp_home / "data" / "learnings.jsonl"
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text('{"id":"1","content":"ok"}\nnot-json\n{"id":"2","content":"ok"}\n')
    records = store.list_all()
    assert len(records) == 2


def test_list_all_many_lines_preserves_order(tmp_home):
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore
    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")
    for i in range(200):
        store.write_learning(type="root-cause", content=f"R{i}", source="user", source_session_id="S")
    records = store.list_all()
    assert len(records) == 200
    assert records[0]["content"] == "R0"
    assert records[-1]["content"] == "R199"


def test_concurrent_writes_no_line_lost(tmp_home):
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore
    bootstrap(tmp_home)
    store = LearningsStore(tmp_home / "data")
    errors = []
    barrier = threading.Barrier(2)

    def w(pid, n):
        barrier.wait()
        for i in range(n):
            try:
                store.write_learning(
                    type="anti-pattern",
                    content=f"p{pid}s{i}",
                    source="user",
                    source_session_id="S",
                )
            except Exception as e:
                errors.append(e)

    t1 = threading.Thread(target=w, args=(1, 50))
    t2 = threading.Thread(target=w, args=(2, 50))
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert not errors
    records = store.list_all()
    assert len(records) == 100
    contents = {r["content"] for r in records}
    for pid in (1, 2):
        for i in range(50):
            assert f"p{pid}s{i}" in contents
