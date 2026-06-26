"""
Project model for aede.

A Project represents a user-opened project directory. Projects are first-class
entities with their own lifecycle: they persist even when all sessions are
deleted, and are only removed by explicit user action.
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Any
from ulid import ULID


def validate_project_dir(path: str) -> Path:
    """Resolve and validate a project directory path.

    Raises ValueError if the resolved path is dangerously broad:
      - Filesystem root ("/", "C:\\", etc.)
      - The user's home directory
      - Any ancestor of the user's home directory
      - Any ancestor of the current working directory
      - Paths only one level from the filesystem root (e.g. "/home", "C:\\Users")

    Returns the resolved Path on success.

    Rationale: ``delete_project_folder`` calls ``shutil.rmtree`` on the
    registered path.  A malicious or accidental POST /api/projects with
    ``project_dir`` set to ``~`` or ``C:\\`` would chain into wiping the
    entire home dir or drive.  This validator is the single chokepoint for
    both registration and deletion (defence-in-depth).
    """
    resolved = Path(path).expanduser().resolve()

    # Reject filesystem root (e.g. "/" on POSIX, "C:\" on Windows)
    if resolved == resolved.root or resolved == resolved.anchor:
        raise ValueError(
            f"Refusing dangerous project_dir: {resolved!r} is a filesystem root"
        )

    # Reject the root via Path.parent check — root.parent == root
    if resolved.parent == resolved:
        raise ValueError(
            f"Refusing dangerous project_dir: {resolved!r} is a filesystem root"
        )

    # Reject drive root on Windows (e.g. Path("C:\\") → parts == ('C:\\',))
    if len(resolved.parts) == 1:
        raise ValueError(
            f"Refusing dangerous project_dir: {resolved!r} is a drive/fs root"
        )

    # Reject paths only one level from the root (e.g. "/home", "C:\\Users")
    # These are typically OS-level directories where rmtree would be catastrophic.
    try:
        root_path = Path(resolved.anchor)
        if resolved.parent == root_path:
            raise ValueError(
                f"Refusing dangerous project_dir: {resolved!r} is only one level "
                f"from the filesystem root {root_path!r}"
            )
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        # Any other resolution error is treated as dangerous
        raise ValueError(f"Refusing dangerous project_dir: {path!r}: {exc}") from exc

    home = Path.home().resolve()

    # Reject home directory itself
    if resolved == home:
        raise ValueError(
            f"Refusing dangerous project_dir: {resolved!r} is the user home directory"
        )

    # Reject any ancestor of home (e.g. "/home", "C:\\Users")
    try:
        home.relative_to(resolved)
        raise ValueError(
            f"Refusing dangerous project_dir: {resolved!r} is a parent of the "
            f"user home directory {home!r}"
        )
    except ValueError as exc:
        if "is a parent of" in str(exc):
            raise
        # relative_to raised ValueError because resolved is NOT an ancestor → OK

    cwd = Path.cwd().resolve()

    # Reject any ancestor of cwd (prevents wiping the working tree)
    try:
        cwd.relative_to(resolved)
        raise ValueError(
            f"Refusing dangerous project_dir: {resolved!r} is a parent of the "
            f"current working directory {cwd!r}"
        )
    except ValueError as exc:
        if "is a parent of" in str(exc):
            raise
        # relative_to raised ValueError because resolved is NOT an ancestor → OK

    return resolved


def generate_project_id() -> str:
    return str(ULID())


class Project:

    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data["id"]
        self.project_dir: str = data["project_dir"]
        self.display_name: str = data["display_name"]
        self.created_at: int = data["created_at"]
        self.updated_at: int = data["updated_at"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_dir": self.project_dir,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def create(cls, db: Any, project_dir: str, display_name: str | None = None) -> "Project":
        pid = generate_project_id()
        name = display_name or Path(project_dir).name
        db.insert_project(id=pid, project_dir=project_dir, display_name=name)
        return cls(db.get_project_by_dir(project_dir))

    @classmethod
    def load(cls, db: Any, project_id: str) -> "Project":
        row = db.get_project(project_id)
        if row is None:
            raise KeyError(f"Project not found: {project_id}")
        return cls(row)

    @classmethod
    def list_all(cls, db: Any) -> list["Project"]:
        return [cls(r) for r in db.list_projects()]

    def delete(self, db: Any) -> None:
        db.delete_project(self.id)
