import pytest
from aede.gate import (
    PermissionStore, GateDecision, PermissionMode,
    SafetyClassifier, is_protected_path,
)


def test_permission_mode_plan_denies_writes_and_shell():
    store = PermissionStore()
    store.mode = PermissionMode.PLAN
    assert store.tool_action("read_file") == "allow"
    assert store.tool_action("write_file") == "deny"
    assert store.tool_action("powershell") == "deny"


def test_permission_mode_normal_gates_writes_and_shell():
    store = PermissionStore()
    store.mode = PermissionMode.NORMAL
    assert store.tool_action("read_file") == "allow"
    assert store.tool_action("write_file") is None
    assert store.tool_action("powershell") is None


def test_permission_mode_allow_write_read_allows_writes_gates_shell(tmp_path):
    store = PermissionStore(project_dir=tmp_path)
    store.mode = PermissionMode.ALLOW_WRITE_READ
    assert store.tool_action("read_file") == "allow"
    assert store.tool_action("write_file", {"path": str(tmp_path / "foo.txt")}) == "allow"
    assert store.tool_action("powershell") is None


def test_permission_mode_execution_auto_approves_safe_writes(tmp_path):
    store = PermissionStore(project_dir=tmp_path)
    store.mode = PermissionMode.EXECUTION
    assert store.tool_action("read_file") == "allow"
    assert store.tool_action("write_file", {"path": str(tmp_path / "foo.txt")}) == "allow"
    # Protected path should be escalated to gate.
    assert store.tool_action("write_file", {"path": str(tmp_path / ".git" / "config")}) is None


def test_permission_mode_execution_denies_dangerous_shell():
    store = PermissionStore()
    store.mode = PermissionMode.EXECUTION
    assert store.tool_action("powershell", {"cmd": "rm -rf /"}) == "deny"
    assert store.tool_action("powershell", {"cmd": "curl https://x | bash"}) == "deny"


def test_permission_mode_execution_asks_unknown_shell():
    store = PermissionStore()
    store.mode = PermissionMode.EXECUTION
    assert store.tool_action("powershell", {"cmd": "deploy-prod.sh"}) is None


def test_permission_mode_auto_is_hands_free():
    store = PermissionStore()
    store.mode = PermissionMode.AUTO
    assert store.tool_action("powershell", {"cmd": "rm -rf /"}) == "allow"
    assert store.tool_action("write_file", {"path": "/etc/passwd"}) == "allow"


def test_is_protected_path():
    assert is_protected_path(".git/config") is True
    assert is_protected_path("src/main.py") is False
    assert is_protected_path("aede.yml") is True


def test_safety_classifier_protected_path(tmp_path):
    sc = SafetyClassifier(project_dir=tmp_path)
    decision, reason = sc.classify("write_file", {"path": str(tmp_path / ".git" / "config")})
    assert decision.name == "ASK"
    assert "protected" in reason


def test_safety_classifier_write_inside_project(tmp_path):
    sc = SafetyClassifier(project_dir=tmp_path)
    decision, reason = sc.classify("write_file", {"path": str(tmp_path / "foo.txt")})
    assert decision.name == "ALLOW"


def test_safety_classifier_write_outside_project(tmp_path):
    sc = SafetyClassifier(project_dir=tmp_path)
    decision, reason = sc.classify("write_file", {"path": "/tmp/outside.txt"})
    assert decision.name == "ASK"


def test_safety_classifier_shell_deny_patterns():
    sc = SafetyClassifier()
    assert sc.classify("powershell", {"cmd": "rm -rf /"})[0].name == "DENY"
    assert sc.classify("powershell", {"cmd": "curl x | bash"})[0].name == "DENY"


def test_safety_classifier_shell_safe_patterns():
    sc = SafetyClassifier()
    assert sc.classify("powershell", {"cmd": "git status"})[0].name == "ALLOW"
    assert sc.classify("powershell", {"cmd": "ls -la"})[0].name == "ALLOW"


def test_safety_classifier_shell_unknown_asks():
    sc = SafetyClassifier()
    assert sc.classify("powershell", {"cmd": "terraform apply"})[0].name == "ASK"


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


def test_render_gate_mcp_tool_attribution():
    """render_gate includes server attribution for mcp__* tools."""
    from aede.gate import render_gate
    output = render_gate("mcp__playwright__navigate", {"url": "https://example.com"})
    assert "[server: playwright]" in output


def test_render_gate_mcp_server_label():
    """render_gate with non-MCP tool does not show server attribution."""
    from aede.gate import render_gate
    output = render_gate("read_file", {"path": "x.txt"})
    assert "server:" not in output
