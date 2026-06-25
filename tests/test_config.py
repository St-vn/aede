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
    assert raw["model"] == "claude-sonnet-4-6"
    assert raw["compaction_threshold"] == 0.85
    assert raw["tool_output_max_tokens"] == 8000
    assert raw["shell"] == "powershell"
    assert raw["batch_approval_max"] == 20


def test_bootstrap_idempotent(tmp_home):
    bootstrap(tmp_home)
    bootstrap(tmp_home)
    assert (tmp_home / "config.yml").exists()


def test_load_config_defaults(tmp_home):
    bootstrap(tmp_home)
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.model == "claude-sonnet-4-6"
    assert cfg.shell == "powershell"


def test_load_config_global_overrides_default(tmp_home, tmp_path):
    bootstrap(tmp_home)
    (tmp_home / "config.yml").write_text(
        yaml.dump({"auto_approve": ["read_file", "list_dir"]})
    )
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert "read_file" in cfg.auto_approve


def test_load_config_global_key_override(tmp_home):
    bootstrap(tmp_home)
    cfg_path = tmp_home / "config.yml"
    raw = yaml.safe_load(cfg_path.read_text())
    raw["model"] = "claude-opus-4-20250514"
    cfg_path.write_text(yaml.dump(raw))
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.model == "claude-opus-4-20250514"


def test_config_provenance_sources(tmp_home, tmp_path):
    bootstrap(tmp_home)
    global_path = tmp_home / "config.yml"
    global_path.write_text(yaml.dump({"model": "global-model", "batch_approval_max": 15}))
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({"shell": "cmd"}))
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.model == "global-model"
    assert cfg.shell == "cmd"
    assert cfg.compaction_threshold == 0.85
    assert cfg.sources["model"] == "global"
    assert cfg.sources["shell"] == "project"
    assert cfg.sources["compaction_threshold"] == "default"


def test_write_config_value_scalar(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    from aede.config import write_config_value
    write_config_value(scope="project", key="batch_approval_max", value="10", home=tmp_home, project_dir=project_dir)
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.batch_approval_max == 10
    assert cfg.sources["batch_approval_max"] == "project"
    write_config_value(scope="global", key="compaction_threshold", value="0.95", home=tmp_home, project_dir=project_dir)
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.compaction_threshold == 0.95
    assert cfg.sources["compaction_threshold"] == "global"


def test_write_config_value_auto_approve_list(tmp_home, tmp_path):
    bootstrap(tmp_home)
    from aede.config import write_config_value
    write_config_value(scope="global", key="auto_approve", value="read_file", action="add", home=tmp_home)
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert "read_file" in cfg.auto_approve
    write_config_value(scope="global", key="auto_approve", value="write_file", action="add", home=tmp_home)
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert set(cfg.auto_approve) == {"read_file", "write_file"}
    write_config_value(scope="global", key="auto_approve", value="read_file", action="remove", home=tmp_home)
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.auto_approve == ["write_file"]


def test_default_grounding_and_critic_flags(tmp_home):
    from aede.config import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["grounding_enabled"] is True
    assert DEFAULT_CONFIG["critic_enabled"] is False
    assert DEFAULT_CONFIG["critic_model"] is None
    assert DEFAULT_CONFIG["critic_api_base_url"] is None


def test_config_round_trip_critic(tmp_home, tmp_path):
    import yaml
    from aede.config import load_config
    bootstrap(tmp_home)
    (tmp_home / "config.yml").write_text(
        yaml.dump({"critic_enabled": True, "critic_api_base_url": "https://openrouter.ai/api/v1"})
    )
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(
        yaml.dump({"critic_model": "claude-haiku-4-20250514", "grounding_enabled": False})
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


def test_providers_block_round_trip(tmp_home, tmp_path):
    import yaml
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(
        yaml.dump({
            "providers": {
                "opencode-zen": {"api_key_env": "OPENCODE_ZEN_API_KEY", "base_url": "https://opencode.ai/zen/v1"},
                "opencode-go": {"api_key_env": "OPENCODE_GO_API_KEY", "base_url": "https://opencode.ai/zen/go"},
            },
        })
    )
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert "opencode-zen" in cfg.providers
    assert cfg.providers["opencode-zen"]["api_key_env"] == "OPENCODE_ZEN_API_KEY"


def test_providers_default_empty(tmp_home):
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.providers == {}


def test_mcp_config_accepts_camelCase(tmp_home):
    from aede.config import AedeConfig
    data = {
        "mcpServers": {
            "playwright": {"command": "npx", "args": ["-y", "@playwright/mcp"]},
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


def test_voice_config_defaults_in_default_config():
    from aede.config import DEFAULT_CONFIG
    assert "voice_input_enabled" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["voice_input_enabled"] is False
    assert "voice_wake_word_enabled" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["voice_wake_word_enabled"] is False


def test_voice_config_defaults_on_empty(tmp_home):
    cfg = AedeConfig(data={}, home=tmp_home)
    assert cfg.voice_input_enabled is False
    assert cfg.voice_wake_word_enabled is False


def test_voice_config_can_be_set_true(tmp_home):
    cfg = AedeConfig(data={"voice_input_enabled": True, "voice_wake_word_enabled": True}, home=tmp_home)
    assert cfg.voice_input_enabled is True
    assert cfg.voice_wake_word_enabled is True


def test_voice_config_round_trip_through_write(tmp_home):
    from aede.config import write_config_value
    write_config_value(scope="global", key="voice_input_enabled", value=True, home=tmp_home)
    write_config_value(scope="global", key="voice_wake_word_enabled", value=True, home=tmp_home)
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.voice_input_enabled is True
    assert cfg.voice_wake_word_enabled is True


def test_fde_enabled_defaults_to_false(tmp_home):
    cfg = AedeConfig(data={}, home=tmp_home)
    assert cfg.fde_enabled is False


def test_fde_enabled_can_be_set(tmp_home):
    cfg = AedeConfig(data={"fde_enabled": True}, home=tmp_home)
    assert cfg.fde_enabled is True


def test_fde_endpoint_defaults_to_none(tmp_home):
    cfg = AedeConfig(data={}, home=tmp_home)
    assert cfg.fde_endpoint is None


def test_fde_endpoint_can_be_set(tmp_home):
    cfg = AedeConfig(data={"fde_endpoint": "https://fde.example.com/upload"}, home=tmp_home)
    assert cfg.fde_endpoint == "https://fde.example.com/upload"


def test_bootstrap_creates_fde_dir(tmp_home):
    bootstrap(tmp_home)
    assert (tmp_home / "data" / "fde").exists()


def test_fde_fields_in_default_config():
    from aede.config import DEFAULT_CONFIG
    assert "fde_enabled" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["fde_enabled"] is False
    assert "fde_endpoint" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["fde_endpoint"] is None


def test_fde_settings_via_project_config(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({
        "fde_enabled": True, "fde_endpoint": "https://analytics.example.com/fde",
    }))
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.fde_enabled is True
    assert cfg.fde_endpoint == "https://analytics.example.com/fde"


def test_sandbox_config_defaults_in_default_config():
    from aede.config import DEFAULT_CONFIG
    assert "sandbox_enabled" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["sandbox_enabled"] is False
    assert DEFAULT_CONFIG["sandbox_image"] == "aede-sandbox:latest"
    assert DEFAULT_CONFIG["sandbox_memory"] == "512m"
    assert DEFAULT_CONFIG["sandbox_cpus"] == 1.0
    assert DEFAULT_CONFIG["sandbox_network"] == "off"
    assert DEFAULT_CONFIG["sandbox_pids_limit"] == 256
    assert DEFAULT_CONFIG["sandbox_pull_on_start"] is True
    assert DEFAULT_CONFIG["sandbox_filter_session_search"] is False


def test_sandbox_config_defaults_on_empty(tmp_home):
    cfg = AedeConfig(data={}, home=tmp_home)
    assert cfg.sandbox_enabled is False
    assert cfg.sandbox_image == "aede-sandbox:latest"
    assert cfg.sandbox_memory == "512m"
    assert cfg.sandbox_cpus == 1.0
    assert cfg.sandbox_network == "off"
    assert cfg.sandbox_pids_limit == 256
    assert cfg.sandbox_pull_on_start is True
    assert cfg.sandbox_filter_session_search is False


def test_sandbox_config_can_be_set(tmp_home):
    cfg = AedeConfig(data={
        "sandbox_enabled": True, "sandbox_image": "custom-sandbox:v2",
        "sandbox_memory": "1g", "sandbox_cpus": 2.0, "sandbox_network": "bridge",
        "sandbox_pids_limit": 512, "sandbox_pull_on_start": False,
        "sandbox_filter_session_search": True,
    }, home=tmp_home)
    assert cfg.sandbox_enabled is True
    assert cfg.sandbox_image == "custom-sandbox:v2"
    assert cfg.sandbox_memory == "1g"
    assert cfg.sandbox_cpus == 2.0
    assert cfg.sandbox_network == "bridge"
    assert cfg.sandbox_pids_limit == 512
    assert cfg.sandbox_pull_on_start is False
    assert cfg.sandbox_filter_session_search is True


def test_sandbox_config_round_trip_through_write(tmp_home):
    from aede.config import write_config_value
    write_config_value(scope="global", key="sandbox_enabled", value=True, home=tmp_home)
    write_config_value(scope="global", key="sandbox_image", value="my-sandbox:test", home=tmp_home)
    write_config_value(scope="global", key="sandbox_cpus", value="4.0", home=tmp_home)
    write_config_value(scope="global", key="sandbox_pids_limit", value="128", home=tmp_home)
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.sandbox_enabled is True
    assert cfg.sandbox_image == "my-sandbox:test"
    assert cfg.sandbox_cpus == 4.0
    assert cfg.sandbox_pids_limit == 128


def test_sandbox_config_round_trip_through_global(tmp_home):
    """Sandbox keys (security-critical) round-trip through global config."""
    bootstrap(tmp_home)
    (tmp_home / "config.yml").write_text(yaml.dump({
        "sandbox_enabled": True, "sandbox_image": "global-sandbox:latest",
        "sandbox_memory": "2g", "sandbox_cpus": 3.0, "sandbox_network": "bridge",
        "sandbox_pids_limit": 1024, "sandbox_pull_on_start": False,
        "sandbox_filter_session_search": True,
    }))
    cfg = load_config(home=tmp_home, project_dir=tmp_home)
    assert cfg.sandbox_enabled is True
    assert cfg.sandbox_image == "global-sandbox:latest"
    assert cfg.sandbox_memory == "2g"
    assert cfg.sandbox_cpus == 3.0
    assert cfg.sandbox_network == "bridge"
    assert cfg.sandbox_pids_limit == 1024
    assert cfg.sandbox_pull_on_start is False
    assert cfg.sandbox_filter_session_search is True


# F-01 + F-03 - Security-critical key allowlist (Issue #70)

def test_security_critical_gate_mode_cannot_be_overridden_by_project(tmp_home, tmp_path):
    bootstrap(tmp_home)
    (tmp_home / "config.yml").write_text(yaml.dump({"gate_mode": "normal"}))
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({"gate_mode": "disabled"}))
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.gate_mode == "normal"
    assert cfg.sources["gate_mode"] == "ignored (security-critical, user-level only)"


def test_security_critical_sandbox_enabled_cannot_be_overridden_by_project(tmp_home, tmp_path):
    bootstrap(tmp_home)
    (tmp_home / "config.yml").write_text(yaml.dump({"sandbox_enabled": True}))
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({"sandbox_enabled": False}))
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.sandbox_enabled is True
    assert cfg.sources["sandbox_enabled"] == "ignored (security-critical, user-level only)"


def test_security_critical_api_base_url_cannot_be_overridden_by_project(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({"api_base_url": "https://evil.example"}))
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.api_base_url is None
    assert cfg.sources["api_base_url"] == "ignored (security-critical, user-level only)"


def test_security_critical_sandbox_image_cannot_be_overridden_by_project(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({"sandbox_image": "evil/img:latest"}))
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.sandbox_image == "aede-sandbox:latest"
    assert cfg.sources["sandbox_image"] == "ignored (security-critical, user-level only)"


def test_security_critical_non_security_keys_still_override(tmp_home, tmp_path):
    bootstrap(tmp_home)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "aede.yml").write_text(yaml.dump({"model": "claude-test-foo"}))
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.model == "claude-test-foo"
    assert cfg.sources["model"] == "project"
