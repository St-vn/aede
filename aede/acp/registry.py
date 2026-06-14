from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

_ACP_CACHE_DIR_NAME = "acp-agents"
_ACP_CACHE_FILE = "cache.json"


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


# ---------------------------------------------------------------------------
# ACP npx package cache — skip the 1.5-4s npx version-check on every connect
# ---------------------------------------------------------------------------

_KNOWN_ACP_PACKAGES: set[str] = {
    "@agentclientprotocol/claude-agent-acp",
    "@agentclientprotocol/codex-acp",
}


def _install_dir(home: Path) -> Path:
    return home / _ACP_CACHE_DIR_NAME


def _cache_path(home: Path) -> Path:
    return _install_dir(home) / _ACP_CACHE_FILE


def _load_cache(home: Path) -> dict[str, str]:
    p = _cache_path(home)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(home: Path, cache: dict[str, str]) -> None:
    p = _cache_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _resolve_index_js(package_dir: Path) -> Path | None:
    pkg_json = package_dir / "package.json"
    if not pkg_json.exists():
        return None
    try:
        data = json.loads(pkg_json.read_text(encoding="utf-8"))
        main = data.get("main", "dist/index.js")
        candidate = package_dir / main
        return candidate if candidate.exists() else None
    except (json.JSONDecodeError, OSError):
        return None


def _find_installed_package(home: Path, package_name: str) -> Path | None:
    install_root = _install_dir(home)
    for node_modules_dir in (install_root / "node_modules",):
        if not node_modules_dir.exists():
            continue
        parts = package_name.split("/", 1)
        if len(parts) == 2:
            scope_dir = node_modules_dir / parts[0]
            pkg_dir = scope_dir / parts[1]
        else:
            pkg_dir = node_modules_dir / parts[0]
        if pkg_dir.is_dir():
            return pkg_dir
    return None


def ensure_acp_package(home: Path, command: str, args: list[str]) -> list[str] | None:
    """Resolve or install an npx ACP package, returning a direct ``node`` command.

    If ``command`` is ``"npx"`` and the target package is a known ACP agent,
    this installs the package under ``~/.aede/acp-agents/`` and returns
    ``["node", "/path/to/dist/index.js"]``.  The resolved path is cached in
    ``cache.json`` so subsequent calls skip npm entirely.

    Returns ``None`` to signal "fall back to the original npx command".
    """
    if command != "npx" or not args or args[0] != "-y":
        return None

    package_name = args[1] if len(args) > 1 else ""
    if not package_name or package_name not in _KNOWN_ACP_PACKAGES:
        return None

    cache = _load_cache(home)
    cached_path = cache.get(package_name)

    if cached_path:
        p = Path(cached_path)
        if p.is_file():
            return ["node", str(p)]

    install_root = _install_dir(home)
    install_root.mkdir(parents=True, exist_ok=True)

    pkg_dir = _find_installed_package(home, package_name)
    if pkg_dir is None:
        try:
            subprocess.run(
                ["npm", "install", "--prefix", str(install_root), package_name],
                capture_output=True, text=True, check=True, timeout=120,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError) as exc:
            logger.warning("ACP cache install failed for %s: %s", package_name, exc)
            return None
        pkg_dir = _find_installed_package(home, package_name)
        if pkg_dir is None:
            return None

    index_js = _resolve_index_js(pkg_dir)
    if index_js is None:
        return None

    cache[package_name] = str(index_js)
    _save_cache(home, cache)
    return ["node", str(index_js)]
