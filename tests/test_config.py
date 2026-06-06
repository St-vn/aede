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


def test_edit_config_file_spawns_editor(tmp_home, tmp_path):
    from unittest.mock import patch
    from aede.config import edit_config_file

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with patch("subprocess.run") as mock_run, patch.dict("os.environ", {"EDITOR": "dummy-editor"}):
        path = edit_config_file(scope="project", home=tmp_home, project_dir=project_dir)
        assert path == project_dir / "aede.yml"
        mock_run.assert_called_once_with(["dummy-editor", str(path)])

