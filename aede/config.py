"""
Configuration loading for aede.

Merges defaults, a global ``~/.aede/config.yml``, and an optional
per-project ``aede.yml`` into a single ``AedeConfig`` object.
Also provides ``bootstrap`` to create the home directory tree on first run.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import os


DEFAULT_CONFIG: dict[str, Any] = {
    "model": "claude-sonnet-4-20250514",
    "data_dir": None,  # resolved at load time to home/data
    "context_window": 200000,
    "compaction_threshold": 0.85,
    "tool_output_max_tokens": 8000,
    "shell": "powershell",
    "wsl_distro": "",
    "batch_approval_max": 20,
    "auto_approve": [],
    "model_prices": {},
    "api_base_url": None,  # None = Anthropic direct; set to OpenAI-compatible base URL (e.g. https://openrouter.ai/api/v1) for non-Anthropic models via OpenAI SDK
    "reasoning_effort": "auto",  # auto | none | low | medium | high | xhigh | max
    "thinking_budget": 0,  # 0 = auto/default, otherwise token count (min 1024)
    # Basic Correctness — Phase 2
    "grounding_enabled": True,
    "critic_enabled": False,
    "critic_model": None,
    "critic_api_base_url": None,
    # Ollama embedding settings (Phase 2 Memory)
    "ollama_base_url": "http://localhost:11434",
    "ollama_embed_model": "nomic-embed-text",
    "ollama_timeout_s": 5,
    # Learnings retrieval settings (Phase 2 Memory)
    "learnings_top_k": 5,
    "learnings_max_tokens": 2000,
    # Provider configurations (e.g. opencode-zen, opencode-go)
    "providers": {},
    # Compaction model override — None means use active model
    "compaction_model": None,
    # MCP server configurations
    "mcp_servers": {},
    # OTel observability
    "otel_endpoint": None,  # None = no-op; set to OTLP gRPC endpoint (e.g. http://localhost:4317)
    "otel_service_name": "aede",
}

DEFAULT_CONFIG_YAML = """\
model: claude-sonnet-4-20250514
context_window: 200000
compaction_threshold: 0.85
tool_output_max_tokens: 8000
shell: powershell          # powershell | cmd | wsl
wsl_distro:                # only used when shell: wsl
batch_approval_max: 20

# API provider — leave blank for Anthropic direct (ANTHROPIC_API_KEY)
# For OpenRouter / non-Anthropic models: set api_base_url to the OpenAI-compatible
# base URL and use OPENROUTER_API_KEY env var. The OpenAI SDK appends
# /chat/completions (not /v1/messages), so this URL must NOT include a trailing /v1.
# api_base_url: https://openrouter.ai/api/v1

# Optional: override model pricing (per million tokens)
# model_prices:
#   claude-sonnet-4-20250514:
#     input: 3.00
#     output: 15.00
#     cache_read: 0.30

# Basic Correctness (Phase 2)
# grounding_enabled: true   # Append grounding instruction to system prompt (default true)
# critic_enabled: false      # Run a critic LLM pass before gated writes (default false; costs extra call)
# critic_model:              # Optional separate model for critic; null = same model, critic persona
# critic_api_base_url:       # Optional base URL for critic model (e.g. https://openrouter.ai/api/v1)

# Reasoning / thinking mode
# reasoning_effort: auto     # auto | none | low | medium | high | xhigh | max
# thinking_budget: 0         # 0 = auto/default, otherwise token count (min 1024)
"""


def _aede_home() -> Path:
    """Return the aede home directory from ``AEDE_HOME`` or ``~/.aede``."""
    env = os.environ.get("AEDE_HOME")
    if env:
        return Path(env)
    return Path.home() / ".aede"


def bootstrap(home: Path | None = None) -> None:
    """Create the aede home directory tree and write a default config if absent.

    Idempotent — safe to call on every launch.
    """
    if home is None:
        home = _aede_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "data").mkdir(exist_ok=True)
    (home / "data" / "sessions").mkdir(exist_ok=True)
    (home / "skills").mkdir(exist_ok=True)
    (home / "agents").mkdir(exist_ok=True)
    cfg_path = home / "config.yml"
    if not cfg_path.exists():
        cfg_path.write_text(DEFAULT_CONFIG_YAML)


class AedeConfig:
    """Resolved, type-annotated view of the merged aede configuration.

    Constructed by ``load_config``; do not instantiate directly in application
    code.
    """

    def __init__(self, data: dict[str, Any], home: Path, sources: dict[str, str] | None = None, project_dir: Path | None = None) -> None:
        self.model: str = data.get("model", DEFAULT_CONFIG["model"])
        self.context_window: int = data.get("context_window", DEFAULT_CONFIG["context_window"])
        self.compaction_threshold: float = data.get("compaction_threshold", DEFAULT_CONFIG["compaction_threshold"])
        self.tool_output_max_tokens: int = data.get("tool_output_max_tokens", DEFAULT_CONFIG["tool_output_max_tokens"])
        self.shell: str = data.get("shell", DEFAULT_CONFIG["shell"])
        self.wsl_distro: str = data.get("wsl_distro") or ""
        self.batch_approval_max: int = data.get("batch_approval_max", DEFAULT_CONFIG["batch_approval_max"])
        self.auto_approve: list[str] = data.get("auto_approve") or []
        self.model_prices: dict[str, Any] = data.get("model_prices") or {}
        self.api_base_url: str | None = data.get("api_base_url") or None
        # Reasoning / thinking mode
        self.reasoning_effort: str = data.get("reasoning_effort", "auto")
        self.thinking_budget: int = data.get("thinking_budget", 0)
        # Basic Correctness — Phase 2
        self.grounding_enabled: bool = data.get("grounding_enabled", True)
        self.critic_enabled: bool = data.get("critic_enabled", False)
        self.critic_model: str | None = data.get("critic_model") or None
        self.critic_api_base_url: str | None = data.get("critic_api_base_url") or None
        # Ollama embedding settings
        self.ollama_base_url: str = data.get("ollama_base_url", DEFAULT_CONFIG["ollama_base_url"])
        self.ollama_embed_model: str = data.get("ollama_embed_model", DEFAULT_CONFIG["ollama_embed_model"])
        self.ollama_timeout_s: int = data.get("ollama_timeout_s", DEFAULT_CONFIG["ollama_timeout_s"])
        # Learnings retrieval settings
        self.learnings_top_k: int = data.get("learnings_top_k", DEFAULT_CONFIG["learnings_top_k"])
        self.learnings_max_tokens: int = data.get("learnings_max_tokens", DEFAULT_CONFIG["learnings_max_tokens"])
        # Provider configurations (e.g. opencode-zen, opencode-go)
        self.providers: dict[str, Any] = data.get("providers") or {}
        # Compaction model override — None means use active model
        self.compaction_model: str | None = data.get("compaction_model") or None
        # MCP server configurations
        raw_mcp = data.get("mcp_servers") or data.get("mcpServers") or {}
        from aede.mcp.client import _parse_mcp_servers
        self.mcp_servers = _parse_mcp_servers(raw_mcp)
        raw_data_dir = data.get("data_dir")
        if raw_data_dir:
            self.data_dir = Path(raw_data_dir).expanduser()
        else:
            self.data_dir = home / "data"
        self.home = home
        self.sources: dict[str, str] = sources or {}
        self.project_dir = project_dir
        from aede.instructions import load_soul_def, SoulDef
        self.soul: SoulDef = load_soul_def(home=self.home, project_dir=self.project_dir)
        # OTel observability
        self.otel_endpoint: str | None = data.get("otel_endpoint") or None
        self.otel_service_name: str = data.get("otel_service_name") or "aede"


def load_config(
    home: Path | None = None,
    project_dir: Path | None = None,
) -> AedeConfig:
    """Load and merge config from defaults → global config → project config.

    Args:
        home: aede home directory; defaults to ``_aede_home()``.
        project_dir: Directory to search for ``aede.yml``; defaults to cwd.

    Returns:
        A fully resolved ``AedeConfig`` instance.
    """
    import yaml

    if home is None:
        home = _aede_home()

    bootstrap(home)

    global_path = home / "config.yml"
    global_data: dict[str, Any] = {}
    if global_path.exists():
        global_data = yaml.safe_load(global_path.read_text()) or {}

    project_data: dict[str, Any] = {}
    if project_dir is None:
        project_dir = Path.cwd()
    project_path = project_dir / "aede.yml"
    if project_path.exists():
        project_data = yaml.safe_load(project_path.read_text()) or {}

    merged = {**DEFAULT_CONFIG, **global_data}
    for key, val in project_data.items():
        merged[key] = val

    sources = {}
    for key in DEFAULT_CONFIG:
        if project_data and key in project_data:
            sources[key] = "project"
        elif global_data and key in global_data:
            sources[key] = "global"
        else:
            sources[key] = "default"

    return AedeConfig(merged, home, sources=sources, project_dir=project_dir)


def write_config_value(
    scope: str,
    key: str,
    value: Any,
    action: str | None = None,
    home: Path | None = None,
    project_dir: Path | None = None,
) -> None:
    """Write a configuration value to either global config or project config.

    Coerces type based on DEFAULT_CONFIG type. Supports list actions (add/remove)
    for auto_approve.
    """
    import yaml
    if home is None:
        home = _aede_home()
    if project_dir is None:
        project_dir = Path.cwd()

    if scope == "global":
        file_path = home / "config.yml"
    elif scope == "project":
        file_path = project_dir / "aede.yml"
    else:
        raise ValueError(f"Invalid config scope: {scope}")

    file_path.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if file_path.exists():
        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}

    default_val = DEFAULT_CONFIG.get(key)

    if action in ("add", "remove"):
        if key != "auto_approve":
            raise ValueError(f"List operations only supported on 'auto_approve', not {key!r}")
        curr_list = data.get("auto_approve") or []
        if not isinstance(curr_list, list):
            curr_list = [curr_list] if curr_list else []
        curr_list = [str(x) for x in curr_list]
        if action == "add":
            if value not in curr_list:
                curr_list.append(value)
        elif action == "remove":
            if value in curr_list:
                curr_list.remove(value)
        data["auto_approve"] = curr_list
    else:
        if isinstance(default_val, int) and not isinstance(default_val, bool):
            coerced = int(value)
        elif isinstance(default_val, float):
            coerced = float(value)
        elif isinstance(default_val, bool):
            if str(value).lower() in ("true", "1", "yes"):
                coerced = True
            else:
                coerced = False
        else:
            coerced = str(value)
        data[key] = coerced

    file_path.write_text(yaml.safe_dump(data, default_flow_style=False), encoding="utf-8")


def edit_config_file(scope: str, home: Path | None = None, project_dir: Path | None = None) -> Path:
    """Launch user editor ($EDITOR, notepad.exe, or vi) on config file."""
    if home is None:
        home = _aede_home()
    if project_dir is None:
        project_dir = Path.cwd()

    if scope == "global":
        file_path = home / "config.yml"
        bootstrap(home)
    elif scope == "project":
        file_path = project_dir / "aede.yml"
        if not file_path.exists():
            file_path.write_text("# project-local configuration\n", encoding="utf-8")
    else:
        raise ValueError(f"Invalid config scope: {scope}")

    import sys
    import os
    import subprocess

    editor = os.environ.get("EDITOR")
    if not editor:
        if sys.platform == "win32":
            editor = "notepad.exe"
        else:
            editor = "vi"

    subprocess.run([editor, str(file_path)])
    return file_path
