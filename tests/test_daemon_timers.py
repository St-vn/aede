import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from aede.daemon.timers import TimerStore, Timer


def test_timer_store_init(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    assert store.data_dir == tmp_home
    assert store.db_path == tmp_home / "daemon_timers.db"


def test_timer_store_creates_db(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    assert store.db_path.exists()


def test_add_timer(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    timer = store.add_timer(delay_s=60, action="ping", label="test timer")
    assert timer.id is not None
    assert timer.delay_s == 60
    assert timer.action == "ping"
    assert timer.label == "test timer"
    assert timer.fire_at > 0
    assert timer.fired is False


def test_add_timer_without_label(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    timer = store.add_timer(delay_s=30, action="notify")
    assert timer.label == ""


def test_get_timer(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    added = store.add_timer(delay_s=120, action="ping")
    fetched = store.get_timer(added.id)
    assert fetched is not None
    assert fetched.id == added.id
    assert fetched.delay_s == 120


def test_get_timer_not_found(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    assert store.get_timer("nonexistent") is None


def test_list_timers(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    t1 = store.add_timer(delay_s=10, action="ping", label="first")
    t2 = store.add_timer(delay_s=20, action="notify", label="second")
    timers = store.list_timers()
    assert len(timers) == 2
    ids = {t.id for t in timers}
    assert t1.id in ids
    assert t2.id in ids


def test_delete_timer(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    added = store.add_timer(delay_s=60, action="ping")
    assert store.get_timer(added.id) is not None
    store.delete_timer(added.id)
    assert store.get_timer(added.id) is None


def test_delete_nonexistent_timer(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    store.delete_timer("nonexistent")  # should not raise


def test_mark_fired(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    added = store.add_timer(delay_s=60, action="ping")
    assert added.fired is False
    store.mark_fired(added.id)
    fetched = store.get_timer(added.id)
    assert fetched is not None
    assert fetched.fired is True


def test_due_timers(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    past = int(time.time()) - 10
    future = int(time.time()) + 3600
    t1 = store.add_timer(delay_s=5, action="ping")
    store._set_fire_at(t1.id, past)
    store.add_timer(delay_s=3600, action="notify")
    store._set_fire_at(t1.id, past)
    due = store.get_due_timers()
    assert len(due) >= 1


def test_persistence_across_restarts(tmp_home):
    store1 = TimerStore(data_dir=tmp_home)
    added = store1.add_timer(delay_s=300, action="ping", label="persistent")
    store1.close()
    store2 = TimerStore(data_dir=tmp_home)
    loaded = store2.get_timer(added.id)
    assert loaded is not None
    assert loaded.delay_s == 300
    assert loaded.action == "ping"
    assert loaded.label == "persistent"
    store2.close()


def test_list_timers_empty(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    assert store.list_timers() == []


def test_timer_str(tmp_home):
    store = TimerStore(data_dir=tmp_home)
    timer = store.add_timer(delay_s=60, action="ping", label="every minute")
    s = str(timer)
    assert "Timer" in s
    assert timer.id in s
    assert "every minute" in s
