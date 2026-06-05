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
}

DEFAULT_CONFIG_YAML = """\
model: claude-sonnet-4-20250514
context_window: 200000
compaction_threshold: 0.85
tool_output_max_tokens: 8000
shell: powershell          # powershell | cmd | wsl
wsl_distro:                # only used when shell: wsl
batch_approval_max: 20

# Optional: override model pricing (per million tokens)
# model_prices:
#   claude-sonnet-4-20250514:
#     input: 3.00
#     output: 15.00
#     cache_read: 0.30
"""


def _jarvis_home() -> Path:
    env = os.environ.get("JARVIS_HOME")
    if env:
        return Path(env)
    return Path.home() / ".jarvis"


def bootstrap(home: Path | None = None) -> None:
    if home is None:
        home = _jarvis_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "data").mkdir(exist_ok=True)
    (home / "data" / "sessions").mkdir(exist_ok=True)
    cfg_path = home / "config.yml"
    if not cfg_path.exists():
        cfg_path.write_text(DEFAULT_CONFIG_YAML)


class JarvisConfig:
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
        raw_data_dir = data.get("data_dir")
        if raw_data_dir:
            self.data_dir = Path(raw_data_dir).expanduser()
        else:
            self.data_dir = home / "data"
        self.home = home


def load_config(
    home: Path | None = None,
    project_dir: Path | None = None,
) -> JarvisConfig:
    import yaml

    if home is None:
        home = _jarvis_home()

    bootstrap(home)

    global_path = home / "config.yml"
    global_data: dict[str, Any] = {}
    if global_path.exists():
        global_data = yaml.safe_load(global_path.read_text()) or {}

    project_data: dict[str, Any] = {}
    if project_dir is None:
        project_dir = Path.cwd()
    project_path = project_dir / "jarvis.yml"
    if project_path.exists():
        project_data = yaml.safe_load(project_path.read_text()) or {}

    merged = {**DEFAULT_CONFIG, **global_data}
    for key, val in project_data.items():
        merged[key] = val

    return JarvisConfig(merged, home)
