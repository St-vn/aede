"""Run-the-app smoke / verification test (Track 2 /verify).

Boots the real FastAPI app via TestClient (real server.py wiring, real DB, real
config — no mocked endpoints) and exercises the wired stack end to end: health,
session create/list round-trip, and — crucially — the S2 security fix live through
the real /api/projects + delete-folder endpoints (validator + confirm token).

This is the "does the assembled application actually respond" check, distinct from
the per-unit endpoint tests.
"""
import pytest
from pathlib import Path

from fastapi.testclient import TestClient
from aede.server import app
from aede.db import DB


@pytest.fixture
def client(tmp_path):
    from aede.config import load_config
    app.state.db = DB(tmp_path / "verify.db")
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    return TestClient(app)


def test_health_endpoint_responds(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_session_create_and_list_round_trip(client):
    """A created session shows up in the listing — real DB round-trip."""
    created = client.post("/api/sessions", json={"model": "claude-sonnet-4-20250514"})
    assert created.status_code == 200, created.text
    sid = created.json()["id"]

    listing = client.get("/api/sessions")
    assert listing.status_code == 200
    body = listing.json()
    # /api/sessions returns {projects: {...}, global: {sessions: [...]}}.
    # A session with no project_dir lands in global.sessions.
    global_sessions = body["global"]["sessions"]
    assert any(s["id"] == sid for s in global_sessions)


def test_project_create_rejects_dangerous_path_live(client):
    """S2 fix, end-to-end: registering the home directory as a project is rejected."""
    r = client.post("/api/projects", json={"project_dir": str(Path.home())})
    assert r.status_code == 400
    assert "dangerous" in r.text.lower() or "refus" in r.text.lower()


def test_project_create_accepts_normal_path_live(client, tmp_path):
    """A normal nested project dir registers fine through the real endpoint."""
    proj = tmp_path / "myproject"
    proj.mkdir()
    r = client.post("/api/projects", json={"project_dir": str(proj)})
    assert r.status_code == 200, r.text
    assert r.json()["project_dir"]


def test_delete_folder_requires_confirm_live(client, tmp_path):
    """S2 CSRF mitigation, end-to-end: delete-folder without confirm:true is rejected."""
    proj = tmp_path / "deletable"
    proj.mkdir()
    (proj / "f.txt").write_text("x")
    created = client.post("/api/projects", json={"project_dir": str(proj)})
    assert created.status_code == 200, created.text
    pid = created.json()["id"]

    # No confirm -> 400, directory still on disk.
    r = client.post(f"/api/projects/{pid}/delete-folder", json={})
    assert r.status_code == 400
    assert proj.exists()

    # With confirm -> 200, directory removed.
    r = client.post(f"/api/projects/{pid}/delete-folder", json={"confirm": True})
    assert r.status_code == 200, r.text
    assert not proj.exists()
