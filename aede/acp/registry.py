from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json


class AgentTransport(Enum):
    LOCAL = "local"


@dataclass
class AgentConfig:
    name: str
    transport: AgentTransport
    command: str
    args: list[str] = field(default_factory=list)
    credentials_ref: Optional[str] = None
    model_override: Optional[str] = None


class AgentRegistry:
    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / "agents.json"
        self._agents: dict[str, AgentConfig] = {}
        if self._path.exists():
            self._load()

    def add(self, config: AgentConfig) -> None:
        if config.name in self._agents:
            raise ValueError(f"An agent named '{config.name}' already exists")
        self._agents[config.name] = config
        self._save()

    def get(self, name: str) -> AgentConfig:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found")
        return self._agents[name]

    def remove(self, name: str) -> None:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found")
        del self._agents[name]
        self._save()

    def list_all(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def _save(self) -> None:
        data = {
            name: {
                "transport": a.transport.value,
                "command": a.command,
                "args": a.args,
                "credentials_ref": a.credentials_ref,
                "model_override": a.model_override,
            }
            for name, a in self._agents.items()
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        for name, cfg in data.items():
            self._agents[name] = AgentConfig(
                name=name,
                transport=AgentTransport(cfg["transport"]),
                command=cfg["command"],
                args=cfg.get("args", []),
                credentials_ref=cfg.get("credentials_ref"),
                model_override=cfg.get("model_override"),
            )
