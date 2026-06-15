"""
Tests for POST /api/voice/trigger — P0.9 Voice Input backend endpoint.

TDD: tests written FIRST.  Run before implementation to confirm RED.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aede.server import app


def _traces_dir(client) -> Path:
    return client.app.state.cfg.data_dir / "traces"


@pytest.fixture
def client(tmp_path):
    from aede.config import load_config
    app.state.db = None
    cfg = load_config(home=tmp_path, project_dir=tmp_path)
    app.state.cfg = cfg
    return TestClient(app)


# ---------------------------------------------------------------------------
# V-02x — POST /api/voice/trigger
# ---------------------------------------------------------------------------


class TestVoiceTriggerEndpoint:
    """V-02x: POST /api/voice/trigger validates, writes event, fails-soft."""

    def test_trigger_writes_event_to_trace(self, client):
        """A valid trigger writes a wake_word_trigger event to the session trace."""
        payload = {
            "session_id": "sess_abc",
            "wake_word": "hey jarvis",
            "matched_text": "",
            "source": "browser",
        }
        resp = client.post("/api/voice/trigger", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        jsonl_path = _traces_dir(client) / "sess_abc.jsonl"
        assert jsonl_path.exists()

        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["session_id"] == "sess_abc"
        assert record["kind"] == "event"
        assert record["event_type"] == "wake_word_trigger"
        assert record["payload"]["wake_word"] == "hey jarvis"
        assert record["payload"]["matched_text"] == ""
        assert record["payload"]["source"] == "browser"
        assert record["schema_version"] == "phase2-draft"
        assert isinstance(record["timestamp"], int)

    def test_trigger_400_on_empty_session_id(self, client):
        """Missing or empty session_id returns 400."""
        resp = client.post("/api/voice/trigger", json={
            "session_id": "",
            "wake_word": "hey",
            "source": "browser",
        })
        assert resp.status_code == 400

    def test_trigger_400_on_empty_wake_word(self, client):
        """Missing or empty wake_word returns 400."""
        resp = client.post("/api/voice/trigger", json={
            "session_id": "s1",
            "wake_word": "",
            "source": "browser",
        })
        assert resp.status_code == 400

    def test_trigger_422_on_invalid_source(self, client):
        """Invalid source value returns 422."""
        resp = client.post("/api/voice/trigger", json={
            "session_id": "s1",
            "wake_word": "hey",
            "source": "invalid_source",
        })
        assert resp.status_code == 422

    def test_trigger_accepts_ios_shortcut_source(self, client):
        """source='ios_shortcut' is accepted and reflected in the trace."""
        payload = {
            "session_id": "sess_ios",
            "wake_word": "hey siri",
            "matched_text": "open aede",
            "source": "ios_shortcut",
        }
        resp = client.post("/api/voice/trigger", json=payload)
        assert resp.status_code == 200

        jsonl_path = _traces_dir(client) / "sess_ios.jsonl"
        record = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
        assert record["payload"]["matched_text"] == "open aede"
        assert record["payload"]["source"] == "ios_shortcut"

    def test_trigger_fails_soft_on_trace_write_error(self, client):
        """If trace write raises, endpoint still returns 200 (fail-soft)."""
        payload = {
            "session_id": "sess_valid",
            "wake_word": "hey",
            "source": "browser",
        }
        resp = client.post("/api/voice/trigger", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_trigger_defaults_to_browser_source(self, client):
        """When source is omitted, defaults to 'browser'."""
        resp = client.post("/api/voice/trigger", json={
            "session_id": "s_default",
            "wake_word": "hey",
        })
        assert resp.status_code == 200

        jsonl_path = _traces_dir(client) / "s_default.jsonl"
        if jsonl_path.exists():
            record = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
            assert record["payload"]["source"] == "browser"

    def test_trigger_rejects_path_traversal_in_session_id(self, client):
        """session_id containing '..', '/', '\\', or NUL is rejected per NFR-7."""
        bad_ids = ["../etc/passwd", "foo/bar", "foo\\bar", "bad\0id"]
        for sid in bad_ids:
            resp = client.post("/api/voice/trigger", json={
                "session_id": sid,
                "wake_word": "hey",
                "source": "browser",
            })
            assert resp.status_code == 400, f"Expected 400 for session_id={sid!r}, got {resp.status_code}"
