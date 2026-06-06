import pytest
from aede.gate import PermissionStore, GateDecision


def test_permission_store_session_allow():
    store = PermissionStore()
    store.allow_session("powershell")
    assert store.is_allowed("powershell") is True


def test_permission_store_project_allow(tmp_path):
    store = PermissionStore()
    store.allow_project("write_file", project_dir=tmp_path)
    assert store.is_allowed("write_file") is True


def test_permission_store_session_overrides_default():
    store = PermissionStore()
    assert store.is_allowed("powershell") is False
    store.allow_session("powershell")
    assert store.is_allowed("powershell") is True


def test_permission_store_persists_project(tmp_path):
    import yaml
    store = PermissionStore()
    store.allow_project("write_file", project_dir=tmp_path)
    cfg = yaml.safe_load((tmp_path / "aede.yml").read_text())
    assert "write_file" in cfg.get("auto_approve", [])


def test_permission_store_global_allow(tmp_path):
    import yaml
    store = PermissionStore()
    store.allow_global("create_file", global_config_path=tmp_path / "config.yml")
    assert store.is_allowed("create_file") is True


def test_gate_decision_enum():
    assert GateDecision.ALLOW_ONCE.value == "allow_once"
    assert GateDecision.DENY.value == "deny"
