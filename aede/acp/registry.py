from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json


class AgentTransport(Enum):
    LOCAL = "local"


# ---------------------------------------------------------------------------
# Default ACP agent seed data (kept here to avoid circular imports)
# ---------------------------------------------------------------------------

_ACP_CREDENTIALS = {
    "codex": "OPENAI_API_KEY",
    "claude-code": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "cursor": "CURSOR_API_KEY",
}

_BASE_AGENTS: list[tuple[str, str, list[str]]] = [
    ("codex",       "npx",          ["-y", "@agentclientprotocol/codex-acp"]),
    ("claude-code", "npx",          ["-y", "@agentclientprotocol/claude-agent-acp"]),
    ("gemini",      "gemini",       ["--acp"]),
    ("cline",       "cline",        ["--acp"]),
    ("cursor",      "cursor-agent", ["--acp"]),
    ("goose",       "goose",        ["acp"]),
]


@dataclass
class AgentConfig:
    name: str
    transport: AgentTransport
    command: str
    args: list[str] = field(default_factory=list)
    credentials_ref: Optional[str] = None
    model_override: Optional[str] = None
    thinking_budget: int = 0


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

    def upsert(self, config: AgentConfig) -> AgentConfig:
        self._agents[config.name] = config
        self._save()
        return config

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
                "thinking_budget": a.thinking_budget,
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
                thinking_budget=cfg.get("thinking_budget", 0),
            )


def seed_default_agents(registry: "AgentRegistry") -> None:
    """Register the 6 built-in ACP agents if they are not already present.

    Only adds entries that are missing — user-edited configs in agents.json
    are never overwritten.  Safe to call multiple times (idempotent).
    """
    for name, command, args in _BASE_AGENTS:
        try:
            registry.get(name)
        except KeyError:
            registry.add(AgentConfig(
                name=name,
                transport=AgentTransport.LOCAL,
                command=command,
                args=args,
                credentials_ref=_ACP_CREDENTIALS.get(name),
            ))
