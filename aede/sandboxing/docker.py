from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import re


@dataclass
class SandboxConfig:
    enabled: bool = False
    image: str = "python:3.12-slim"
    workspace_mount: str = "/workspace"
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SandboxConfig:
        return cls(
            enabled=raw.get("enabled", False),
            image=raw.get("image", "python:3.12-slim"),
            workspace_mount=raw.get("workspace_mount", "/workspace"),
            memory_limit=raw.get("memory_limit", "512m"),
            cpu_limit=float(raw.get("cpu_limit", 1.0)),
            env=raw.get("env", {}),
        )


def container_name(session_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
    return f"aede-{safe}"
