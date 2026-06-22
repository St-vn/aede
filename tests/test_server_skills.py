"""Tests for skills API endpoints — especially the registry-first path resolution.

The fix: ``_find_skill_path`` resolves from the registry's ``source_path``
(rather than guessing from name), so skills discovered from ``~/.claude/skills/``
or other non-standard locations can be edited, deleted, and opened without 404s.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aede.db import DB
from aede.server import app
from aede.skills.schema import SkillDef


# ── helpers ──────────────────────────────────────────────────────────────


def _make_skill_file(path: Path, name: str, description: str = "Test skill") -> None:
    """Write a valid skill .md file to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""---
name: {name}
description: {description}
trigger_phrases:
  - test {name}
---

# {name.title()}

Body of {name}.
"""
    path.write_text(content)


def _skill_def(name: str, path: Path) -> SkillDef:
    """Create a SkillDef with the given source_path (no file I/O)."""
    return SkillDef(
        name=name,
        description="Test skill",
        trigger_phrases=[f"test {name}"],
        body=f"Body of {name}.",
        source_path=path,
    )


# ── Unit: _find_skill_path ──────────────────────────────────────────────


class TestFindSkillPath:
    """Unit tests for the ``_find_skill_path`` helper."""

    def test_uses_registry_source_path_when_available(self, tmp_path: Path):
        """Registry ``source_path`` takes priority over constructed path."""
        from unittest.mock import MagicMock

        from aede.server import _find_skill_path

        # Skill lives in a claude-like location
        claude_path = tmp_path / "claude" / "skills" / "test-skill" / "SKILL.md"
        _make_skill_file(claude_path, "test-skill")

        request = MagicMock()
        request.app.state.skill_registry = {
            "test-skill": _skill_def("test-skill", claude_path),
        }
        request.app.state.cfg.home = tmp_path / "aede"

        result = _find_skill_path(request, "test-skill")
        assert result == claude_path

    def test_falls_back_to_resolve_when_not_in_registry(self, tmp_path: Path):
        """Skills not in registry use the fallback ``_resolve_skill_path``."""
        from unittest.mock import MagicMock

        from aede.server import _find_skill_path

        home = tmp_path / "aede"
        request = MagicMock()
        request.app.state.skill_registry = {}
        request.app.state.cfg.home = home

        result = _find_skill_path(request, "unknown-skill")
        assert result == home / "skills" / "unknown-skill.md"

    def test_falls_back_when_source_path_is_none(self, tmp_path: Path):
        """A registry entry with ``source_path=None`` should still fall back."""
        from unittest.mock import MagicMock

        from aede.server import _find_skill_path

        home = tmp_path / "aede"
        sd = SkillDef(
            name="no-path",
            description="No source path set",
            trigger_phrases=["test no-path"],
            body="None.",
            source_path=None,
        )
        request = MagicMock()
        request.app.state.skill_registry = {"no-path": sd}
        request.app.state.cfg.home = home

        result = _find_skill_path(request, "no-path")
        assert result == home / "skills" / "no-path.md"


# ── Integration: PUT / DELETE / OPEN with claude-fallback skills ────────


class TestSkillEndpointsWithClaudeFallback:
    """PUT/DELETE/OPEN should work on skills from non-standard locations."""

    @pytest.fixture
    def db(self, tmp_path: Path) -> DB:
        return DB(tmp_path / "test.db")

    @pytest.fixture
    def client(self, db: DB, tmp_path: Path) -> TestClient:
        from aede.config import load_config

        app.state.db = db
        app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
        return TestClient(app)

    # -- helpers ----------------------------------------------------------

    def _seed_registry(self, name: str, source_path: Path) -> None:
        """Inject a single skill directly into the app's registry.

        This bypasses ``load_skills()`` so we can test with skills that live
        outside the standard ``~/.aede/skills/`` layout (e.g. claude fallback).
        """
        app.state.skill_registry = {name: _skill_def(name, source_path)}

    # -- update (PUT) -----------------------------------------------------

    def test_update_skill_from_claude_location(self, client: TestClient, tmp_path: Path):
        """PUT resolves from registry source_path, not constructed path."""
        claude_path = tmp_path / "claude" / "skills" / "update-me" / "SKILL.md"
        _make_skill_file(claude_path, "update-me")
        self._seed_registry("update-me", claude_path)

        resp = client.put(
            "/api/skills/update-me",
            json={"name": "update-me", "description": "Updated by test"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "name": "update-me"}

        # Verify the file *at the claude location* was actually updated
        import yaml

        parts = claude_path.read_text("utf-8").split("---", 2)
        meta = yaml.safe_load(parts[1])
        assert meta["description"] == "Updated by test"

    def test_update_skill_keeps_normal_path_when_in_standard_dir(
        self, client: TestClient, tmp_path: Path
    ):
        """Skills in the standard ``~/.aede/skills/`` dir still work."""
        normal_path = tmp_path / "skills" / "normal-skill.md"
        _make_skill_file(normal_path, "normal-skill")
        self._seed_registry("normal-skill", normal_path)

        resp = client.put(
            "/api/skills/normal-skill",
            json={"name": "normal-skill", "description": "Still works"},
        )
        assert resp.status_code == 200

    def test_update_unknown_skill_returns_404(self, client: TestClient):
        """PUT on a skill not in registry AND not on disk returns 404."""
        resp = client.put(
            "/api/skills/does-not-exist",
            json={"name": "does-not-exist", "description": "nope"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    # -- delete (DELETE) --------------------------------------------------

    def test_delete_skill_from_claude_location(self, client: TestClient, tmp_path: Path):
        """DELETE resolves from registry source_path."""
        claude_path = tmp_path / "claude" / "skills" / "del-me" / "SKILL.md"
        _make_skill_file(claude_path, "del-me")
        self._seed_registry("del-me", claude_path)

        resp = client.delete("/api/skills/del-me")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "name": "del-me"}
        assert not claude_path.exists()

    def test_delete_unknown_skill_returns_404(self, client: TestClient):
        """DELETE on a non-existent skill returns 404."""
        resp = client.delete("/api/skills/not-here")
        assert resp.status_code == 404

    # -- open (POST /open) ------------------------------------------------

    def test_open_skill_file_from_claude_location(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """POST .../open resolves from registry source_path."""
        claude_path = tmp_path / "claude" / "skills" / "open-me" / "SKILL.md"
        _make_skill_file(claude_path, "open-me")
        self._seed_registry("open-me", claude_path)

        opened: list[str] = []
        # Patch the cross-platform opener (os.startfile is Windows-only and
        # absent on Linux CI, so patching it directly fails there).
        import aede.server
        monkeypatch.setattr(aede.server, "_open_in_default_app", lambda p: opened.append(p))

        resp = client.post("/api/skills/open-me/open")
        assert resp.status_code == 200
        assert str(claude_path) in opened

    def test_open_unknown_skill_returns_404(self, client: TestClient):
        """POST .../open on a non-existent skill returns 404."""
        resp = client.post("/api/skills/ghost/open")
        assert resp.status_code == 404

    # -- cleanup ----------------------------------------------------------

    @pytest.fixture(autouse=True)
    def _reset_app_state(self):
        """Reset per-test app state to avoid cross-test contamination."""
        app.state.db = None
        app.state.cfg = None
        app.state.skill_registry = None
        yield
        app.state.db = None
        app.state.cfg = None
        app.state.skill_registry = None
