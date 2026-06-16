from __future__ import annotations
from unittest.mock import patch


def _client():
    from aede.server import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def _cfg(tmp_home, project):
    from aede.config import AedeConfig
    return AedeConfig({}, home=tmp_home, project_dir=project)


# ── GET ──

def test_get_global_returns_home_agents_md(tmp_home, tmp_path):
    (tmp_home / "AGENTS.md").write_text("# global rules\n", encoding="utf-8")
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, tmp_path)):
        resp = _client().get("/api/project-instructions", params={"scope": "global"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "# global rules\n"
    assert data["filename"] == "AGENTS.md"


def test_get_global_missing_returns_empty(tmp_home, tmp_path):
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, tmp_path)):
        resp = _client().get("/api/project-instructions", params={"scope": "global"})
    assert resp.status_code == 200
    assert resp.json()["content"] == ""


def test_get_project_prefers_agents_md(tmp_home, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "AGENTS.md").write_text("agents content", encoding="utf-8")
    (project / "CLAUDE.md").write_text("claude content", encoding="utf-8")
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, project)):
        resp = _client().get("/api/project-instructions",
                             params={"scope": "project", "project_dir": str(project)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "agents content"
    assert data["filename"] == "AGENTS.md"


def test_get_project_falls_back_to_claude_md(tmp_home, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "CLAUDE.md").write_text("claude content", encoding="utf-8")
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, project)):
        resp = _client().get("/api/project-instructions",
                             params={"scope": "project", "project_dir": str(project)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "claude content"
    assert data["filename"] == "CLAUDE.md"


def test_get_project_requires_project_dir(tmp_home, tmp_path):
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, None)):
        resp = _client().get("/api/project-instructions", params={"scope": "project"})
    assert resp.status_code == 400


# ── PUT ──

def test_put_global_writes_home_agents_md(tmp_home, tmp_path):
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, tmp_path)):
        resp = _client().put("/api/project-instructions",
                             json={"scope": "global", "content": "new global"})
    assert resp.status_code == 200
    assert (tmp_home / "AGENTS.md").read_text(encoding="utf-8") == "new global"


def test_put_project_new_file_writes_agents_md(tmp_home, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, project)):
        resp = _client().put("/api/project-instructions",
                             json={"scope": "project", "project_dir": str(project),
                                   "content": "proj rules"})
    assert resp.status_code == 200
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == "proj rules"


def test_put_project_existing_claude_md_updates_in_place(tmp_home, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "CLAUDE.md").write_text("old", encoding="utf-8")
    with patch("aede.server.get_config_for_request", return_value=_cfg(tmp_home, project)):
        resp = _client().put("/api/project-instructions",
                             json={"scope": "project", "project_dir": str(project),
                                   "content": "updated"})
    assert resp.status_code == 200
    # Writes back to the file actually loaded (CLAUDE.md), not a new AGENTS.md.
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == "updated"
    assert not (project / "AGENTS.md").exists()
