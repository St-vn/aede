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
