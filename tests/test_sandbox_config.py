from __future__ import annotations
from pathlib import Path
import yaml


def test_sandbox_config_defaults(tmp_home):
    from aede.config import load_config
    cfg = load_config(home=tmp_home)
    assert cfg.sandbox_enabled is False
    assert cfg.sandbox_image == "aede-sandbox:latest"


def test_sandbox_config_flat_keys(tmp_home):
    global_cfg = tmp_home / "config.yml"
    global_cfg.write_text(yaml.safe_dump({
        "sandbox_enabled": True,
        "sandbox_image": "custom:latest",
        "sandbox_memory": "1g",
    }))
    from aede.config import load_config
    cfg = load_config(home=tmp_home)
    assert cfg.sandbox_enabled is True
    assert cfg.sandbox_image == "custom:latest"
    assert cfg.sandbox_memory == "1g"


def test_sandbox_config_project_override_non_critical(tmp_home):
    project_dir = tmp_home / "proj"
    project_dir.mkdir()
    project_cfg = project_dir / "aede.yml"
    project_cfg.write_text(yaml.safe_dump({"sandbox_pull_on_start": False}))
    from aede.config import load_config
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.sandbox_pull_on_start is False


def test_sandbox_config_has_flat_attrs(tmp_home):
    from aede.config import load_config
    cfg = load_config(home=tmp_home)
    assert hasattr(cfg, "sandbox_enabled")
    assert hasattr(cfg, "sandbox_image")
    assert hasattr(cfg, "sandbox_memory")
