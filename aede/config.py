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
    cfg_path = home / "config.yml"
    if not cfg_path.exists():
        cfg_path.write_text(DEFAULT_CONFIG_YAML)


class AedeConfig:
    """Resolved, type-annotated view of the merged aede configuration.

    Constructed by ``load_config``; do not instantiate directly in application
    code.
    """

    def __init__(self, data: dict[str, Any], home: Path) -> None:
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
        raw_data_dir = data.get("data_dir")
        if raw_data_dir:
            self.data_dir = Path(raw_data_dir).expanduser()
        else:
            self.data_dir = home / "data"
        self.home = home


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

    return AedeConfig(merged, home)
