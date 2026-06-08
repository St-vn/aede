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
