# tests/test_config.py
import pytest
from pathlib import Path
import yaml
from aede.config import load_config, bootstrap, AedeConfig


def test_bootstrap_creates_aede_dir(tmp_home):
    bootstrap(tmp_home)
    assert tmp_home.exists()
    assert (tmp_home / "data").exists()
    assert (tmp_home / "data" / "sessions").exists()
    assert (tmp_home / "config.yml").exists()


def test_bootstrap_writes_default_config(tmp_home):
    bootstrap(tmp_home)
    raw = yaml.safe_load((tmp_home / "config.yml").read_text())
    assert raw["model"] == "claude-sonnet-4-20250514"
    assert raw["compaction_threshold"] == 0.85
    assert raw["tool_output_max_tokens"] == 8000
    assert raw["shell"] == "powershell"
    assert raw["batch_approval_max"] == 20


def test_bootstrap_idempotent(tmp_home):
    bootstrap(tmp_home)
    bootstrap(tmp_home)  # second call must not raise or overwrite
    assert (tmp_home / "config.yml").exists()


def test_load_config_defaults(tmp_home):
    bootstrap(tmp_home)
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.model == "claude-sonnet-4-20250514"
    assert cfg.shell == "powershell"


def test_load_config_project_overrides_global(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(
        yaml.dump({"auto_approve": ["read_file", "list_dir"]})
    )
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert "read_file" in cfg.auto_approve


def test_load_config_global_key_override(tmp_home):
    bootstrap(tmp_home)
    cfg_path = tmp_home / "config.yml"
    raw = yaml.safe_load(cfg_path.read_text())
    raw["model"] = "claude-opus-4-20250514"
    cfg_path.write_text(yaml.dump(raw))
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.model == "claude-opus-4-20250514"


# ---------------------------------------------------------------------------
# Task 8 — config editing, auto-approve modifications, and provenance
# ---------------------------------------------------------------------------

def test_config_provenance_sources(tmp_home, tmp_path):
    bootstrap(tmp_home)
    # 1. Global config has model overridden
    global_path = tmp_home / "config.yml"
    global_path.write_text(yaml.dump({"model": "global-model", "batch_approval_max": 15}))

    # 2. Project config has shell overridden
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({"shell": "cmd"}))

    cfg = load_config(home=tmp_home, project_dir=project_dir)

    # Check effective values
    assert cfg.model == "global-model"
    assert cfg.shell == "cmd"
    assert cfg.compaction_threshold == 0.85  # default

    # Check sources provenance mapping
    assert cfg.sources["model"] == "global"
    assert cfg.sources["shell"] == "project"
    assert cfg.sources["compaction_threshold"] == "default"


def test_write_config_value_scalar(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    from aede.config import write_config_value

    # Set project config key (scalar)
    write_config_value(scope="project", key="batch_approval_max", value="10", home=tmp_home, project_dir=project_dir)

    # Reload and check
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.batch_approval_max == 10
    assert cfg.sources["batch_approval_max"] == "project"

    # Set global config key (scalar with float coercion)
    write_config_value(scope="global", key="compaction_threshold", value="0.95", home=tmp_home, project_dir=project_dir)

    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.compaction_threshold == 0.95
    assert cfg.sources["compaction_threshold"] == "global"


def test_write_config_value_auto_approve_list(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    from aede.config import write_config_value

    # 1. Add "read_file" to project auto_approve
    write_config_value(scope="project", key="auto_approve", value="read_file", action="add", home=tmp_home, project_dir=project_dir)

    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert "read_file" in cfg.auto_approve

    # 2. Add "write_file" to project auto_approve
    write_config_value(scope="project", key="auto_approve", value="write_file", action="add", home=tmp_home, project_dir=project_dir)

    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert set(cfg.auto_approve) == {"read_file", "write_file"}

    # 3. Remove "read_file"
    write_config_value(scope="project", key="auto_approve", value="read_file", action="remove", home=tmp_home, project_dir=project_dir)

    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.auto_approve == ["write_file"]


# ---------------------------------------------------------------------------
# BC-01 — grounding_enabled / critic_enabled / critic_model / critic_api_base_url
# ---------------------------------------------------------------------------

def test_default_grounding_and_critic_flags(tmp_home):
    """DEFAULT_CONFIG must include correct defaults for the four new BC keys."""
    from aede.config import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["grounding_enabled"] is True
    assert DEFAULT_CONFIG["critic_enabled"] is False
    assert DEFAULT_CONFIG["critic_model"] is None
    assert DEFAULT_CONFIG["critic_api_base_url"] is None


def test_config_round_trip_critic(tmp_home, tmp_path):
    """Write critic keys to a project config file, reload, and verify they round-trip."""
    import yaml
    from aede.config import load_config

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(
        yaml.dump({
            "critic_enabled": True,
            "critic_model": "claude-haiku-4-20250514",
            "critic_api_base_url": "https://openrouter.ai/api/v1",
            "grounding_enabled": False,
        })
    )
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.critic_enabled is True
    assert cfg.critic_model == "claude-haiku-4-20250514"
    assert cfg.critic_api_base_url == "https://openrouter.ai/api/v1"
    assert cfg.grounding_enabled is False


def test_edit_config_file_spawns_editor(tmp_home, tmp_path):
    from unittest.mock import patch
    from aede.config import edit_config_file

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {"EDITOR": "dummy-editor"}):
        path = edit_config_file(scope="project", home=tmp_home, project_dir=project_dir)
        assert path == project_dir / "aede.yml"
        mock_run.assert_called_once_with(["dummy-editor", str(path)])


# ---------------------------------------------------------------------------
# P01-02 — providers config block
# ---------------------------------------------------------------------------

def test_providers_block_round_trip(tmp_home, tmp_path):
    """providers: block round-trips through load_config."""
    import yaml
    from aede.config import write_config_value

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(
        yaml.dump({
            "providers": {
                "opencode-zen": {
                    "api_key_env": "OPENCODE_ZEN_API_KEY",
                    "base_url": "https://opencode.ai/zen/v1",
                },
                "opencode-go": {
                    "api_key_env": "OPENCODE_GO_API_KEY",
                    "base_url": "https://opencode.ai/zen/go",
                },
            },
        })
    )
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert "opencode-zen" in cfg.providers
    assert "opencode-go" in cfg.providers
    assert cfg.providers["opencode-zen"]["api_key_env"] == "OPENCODE_ZEN_API_KEY"
    assert cfg.providers["opencode-zen"]["base_url"] == "https://opencode.ai/zen/v1"
    assert cfg.providers["opencode-go"]["api_key_env"] == "OPENCODE_GO_API_KEY"
    assert cfg.providers["opencode-go"]["base_url"] == "https://opencode.ai/zen/go"


def test_providers_default_empty(tmp_home):
    """When no providers: block is set, cfg.providers is empty dict."""
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.providers == {}


def test_mcp_config_accepts_camelCase(tmp_home):
    """AedeConfig accepts mcpServers (camelCase) as alias for mcp_servers."""
    from aede.config import AedeConfig
    from pathlib import Path

    data = {
        "mcpServers": {
            "playwright": {
                "command": "npx",
                "args": ["-y", "@playwright/mcp"],
            },
        },
    }
    cfg = AedeConfig(data=data, home=tmp_home)
    assert "playwright" in cfg.mcp_servers
    assert cfg.mcp_servers["playwright"].command == "npx"


def test_compaction_model_in_default_config():
    from aede.config import DEFAULT_CONFIG
    assert "compaction_model" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["compaction_model"] is None


def test_compaction_model_defaults_to_none(tmp_home):
    cfg = AedeConfig(data={}, home=tmp_home)
    assert cfg.compaction_model is None


def test_compaction_model_round_trip(tmp_home):
    cfg = AedeConfig(data={"compaction_model": "deepseek-v4-flash-free"}, home=tmp_home)
    assert cfg.compaction_model == "deepseek-v4-flash-free"

