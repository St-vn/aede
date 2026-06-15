from __future__ import annotations
from pathlib import Path
import yaml


def test_sandbox_config_wired_in_default(tmp_home):
    from aede.config import load_config
    cfg = load_config(home=tmp_home)
    assert cfg.sandbox.enabled is False
    assert cfg.sandbox.image == "python:3.12-slim"


def test_sandbox_config_reads_from_global(tmp_home):
    global_cfg = tmp_home / "config.yml"
    global_cfg.write_text(yaml.safe_dump({"sandbox": {"enabled": True, "image": "custom:latest"}}))
    from aede.config import load_config
    cfg = load_config(home=tmp_home)
    assert cfg.sandbox.enabled is True
    assert cfg.sandbox.image == "custom:latest"


def test_sandbox_config_reads_from_project(tmp_home):
    project_dir = tmp_home / "proj"
    project_dir.mkdir()
    project_cfg = project_dir / "aede.yml"
    project_cfg.write_text(yaml.safe_dump({"sandbox": {"enabled": True, "memory_limit": "1g"}}))
    from aede.config import load_config
    cfg = load_config(home=tmp_home, project_dir=project_dir)
    assert cfg.sandbox.enabled is True
    assert cfg.sandbox.memory_limit == "1g"


def test_sandbox_config_allows_access(tmp_home):
    from aede.config import load_config
    cfg = load_config(home=tmp_home)
    assert hasattr(cfg, "sandbox")
    assert hasattr(cfg.sandbox, "enabled")
    assert hasattr(cfg.sandbox, "image")
