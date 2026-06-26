# tests/test_project_safety.py
"""
TDD tests for #19 S2 — path-safety validator and CSRF confirm guard.

RED phase: all tests fail before fix because validate_project_dir does not
exist yet and delete-folder has no confirm guard.
"""
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from aede.server import app
from aede.db import DB


# ── Unit tests for validate_project_dir ───────────────────────────────────────


def test_validate_project_dir_rejects_filesystem_root():
    """Filesystem root ('/') must be rejected."""
    from aede.project import validate_project_dir
    with pytest.raises(ValueError):
        validate_project_dir("/")


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="'C:\\' is a Windows drive-root concept; on POSIX it resolves to a normal "
    "subpath. The POSIX root ('/') is covered by test_validate_project_dir_rejects_filesystem_root.",
)
def test_validate_project_dir_rejects_drive_root():
    """Windows drive root (C:\\) must be rejected."""
    from aede.project import validate_project_dir
    with pytest.raises(ValueError):
        validate_project_dir("C:\\")


def test_validate_project_dir_rejects_home():
    """User home directory must be rejected."""
    from aede.project import validate_project_dir
    with pytest.raises(ValueError):
        validate_project_dir(str(Path.home()))


def test_validate_project_dir_rejects_parent_of_cwd():
    """Direct parent of cwd must be rejected."""
    from aede.project import validate_project_dir
    parent = str(Path.cwd().parent)
    with pytest.raises(ValueError):
        validate_project_dir(parent)


def test_validate_project_dir_accepts_normal_nested_dir(tmp_path):
    """A valid nested directory under tmp_path must be accepted."""
    from aede.project import validate_project_dir
    target = tmp_path / "myproject" / "sub"
    target.mkdir(parents=True, exist_ok=True)
    result = validate_project_dir(str(target))
    assert isinstance(result, Path)
    assert result == target.resolve()


# ── Fixtures shared by endpoint tests ─────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "test.db")


@pytest.fixture
def client(db, tmp_path):
    from aede.config import load_config
    app.state.db = db
    app.state.cfg = load_config(home=tmp_path, project_dir=tmp_path)
    return TestClient(app)


# ── Endpoint tests ─────────────────────────────────────────────────────────────


def test_create_project_with_home_dir_returns_400(client):
    """POST /api/projects with project_dir=~home must return 400."""
    response = client.post("/api/projects", json={"project_dir": str(Path.home())})
    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.text}"
    )


def test_delete_folder_without_confirm_returns_400(client, db, tmp_path):
    """delete-folder without confirm:true must return 400 (CSRF guard)."""
    # Register a valid project first
    proj_dir = tmp_path / "safe_project"
    proj_dir.mkdir()
    reg = client.post("/api/projects", json={"project_dir": str(proj_dir)})
    assert reg.status_code == 200
    project_id = reg.json()["id"]

    # Call delete-folder WITHOUT confirm
    response = client.post(f"/api/projects/{project_id}/delete-folder", json={})
    assert response.status_code == 400, (
        f"Expected 400 (missing confirm), got {response.status_code}: {response.text}"
    )


def test_delete_folder_with_confirm_and_valid_dir_returns_200(client, db, tmp_path):
    """delete-folder with confirm:true and valid registered dir must succeed."""
    proj_dir = tmp_path / "deleteable_project"
    proj_dir.mkdir()
    reg = client.post("/api/projects", json={"project_dir": str(proj_dir)})
    assert reg.status_code == 200
    project_id = reg.json()["id"]

    response = client.post(
        f"/api/projects/{project_id}/delete-folder",
        json={"confirm": True},
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )
    # Directory must be gone
    assert not proj_dir.exists(), "Expected project directory to be deleted"
