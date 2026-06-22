import pytest
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from aede.daemon.events import EventStore, WatchEvent, WebhookEvent


def test_event_store_init(tmp_home):
    store = EventStore(data_dir=tmp_home)
    assert store.data_dir == tmp_home
    assert store.db_path == tmp_home / "daemon_events.db"


def test_event_store_creates_db(tmp_home):
    store = EventStore(data_dir=tmp_home)
    assert store.db_path.exists()


def test_add_watch_event(tmp_home):
    store = EventStore(data_dir=tmp_home)
    ev = store.add_watch(path="/tmp/watch", action="notify", label="watch tmp")
    assert ev.id is not None
    assert ev.path == "/tmp/watch"
    assert ev.action == "notify"
    assert ev.label == "watch tmp"
    assert ev.event_type == "watch"
    assert ev.enabled is True


def test_add_watch_event_default_label(tmp_home):
    store = EventStore(data_dir=tmp_home)
    ev = store.add_watch(path="/data", action="sync")
    assert ev.label == ""


def test_add_webhook_event(tmp_home):
    store = EventStore(data_dir=tmp_home)
    ev = store.add_webhook(route="/hooks/github", action="deploy", label="github push")
    assert ev.id is not None
    assert ev.route == "/hooks/github"
    assert ev.action == "deploy"
    assert ev.label == "github push"
    assert ev.event_type == "webhook"
    assert ev.enabled is True


def test_add_webhook_event_default_label(tmp_home):
    store = EventStore(data_dir=tmp_home)
    ev = store.add_webhook(route="/hooks/notify", action="notify")
    assert ev.label == ""


def test_get_event(tmp_home):
    store = EventStore(data_dir=tmp_home)
    added = store.add_watch(path="/tmp", action="notify")
    fetched = store.get_event(added.id)
    assert fetched is not None
    assert fetched.id == added.id
    assert fetched.path == "/tmp"


def test_get_event_not_found(tmp_home):
    store = EventStore(data_dir=tmp_home)
    assert store.get_event("nonexistent") is None


def test_list_events(tmp_home):
    store = EventStore(data_dir=tmp_home)
    ev1 = store.add_watch(path="/tmp", action="notify", label="tmp")
    ev2 = store.add_webhook(route="/hooks/test", action="test", label="test")
    events = store.list_events()
    assert len(events) == 2
    ids = {e.id for e in events}
    assert ev1.id in ids
    assert ev2.id in ids


def test_list_events_empty(tmp_home):
    store = EventStore(data_dir=tmp_home)
    assert store.list_events() == []


def test_delete_event(tmp_home):
    store = EventStore(data_dir=tmp_home)
    added = store.add_watch(path="/tmp", action="notify")
    assert store.get_event(added.id) is not None
    store.delete_event(added.id)
    assert store.get_event(added.id) is None


def test_delete_nonexistent_event(tmp_home):
    store = EventStore(data_dir=tmp_home)
    store.delete_event("nonexistent")


def test_enable_disable_event(tmp_home):
    store = EventStore(data_dir=tmp_home)
    added = store.add_watch(path="/tmp", action="notify")
    assert added.enabled is True
    store.set_enabled(added.id, False)
    fetched = store.get_event(added.id)
    assert fetched is not None
    assert fetched.enabled is False
    store.set_enabled(added.id, True)
    fetched = store.get_event(added.id)
    assert fetched is not None
    assert fetched.enabled is True


def test_get_events_by_type(tmp_home):
    store = EventStore(data_dir=tmp_home)
    w1 = store.add_watch(path="/tmp", action="notify")
    w2 = store.add_watch(path="/var", action="sync")
    h1 = store.add_webhook(route="/hooks/test", action="test")
    watches = store.get_events_by_type("watch")
    assert len(watches) == 2
    hooks = store.get_events_by_type("webhook")
    assert len(hooks) == 1


def test_persistence_across_restarts(tmp_home):
    store1 = EventStore(data_dir=tmp_home)
    added = store1.add_watch(path="/persistent", action="sync", label="survive")
    store1.close()
    store2 = EventStore(data_dir=tmp_home)
    loaded = store2.get_event(added.id)
    assert loaded is not None
    assert loaded.path == "/persistent"
    assert loaded.action == "sync"
    assert loaded.label == "survive"
    store2.close()


def test_watch_event_to_dict(tmp_home):
    store = EventStore(data_dir=tmp_home)
    ev = store.add_watch(path="/tmp/watch", action="notify", label="test")
    d = ev.to_dict()
    assert d["event_type"] == "watch"
    assert d["path"] == "/tmp/watch"
    assert d["action"] == "notify"


def test_webhook_event_to_dict(tmp_home):
    store = EventStore(data_dir=tmp_home)
    ev = store.add_webhook(route="/hooks/test", action="deploy", label="deploy")
    d = ev.to_dict()
    assert d["event_type"] == "webhook"
    assert d["route"] == "/hooks/test"
    assert d["action"] == "deploy"
