import json
import pytest
from pathlib import Path
from aede.acp.manager import AcpManager, AgentSession, AcpConnectionError
from aede.acp.registry import AgentRegistry, AgentConfig, AgentTransport
from aede.acp.credentials import CredentialProvider


def make_agent_script(tmp_path: Path, name: str, session_id: str) -> Path:
    """Create a fake ACP agent that responds to initialize + session/new."""
    script = tmp_path / f"{name}_agent.py"
    script.write_text(f"""
import sys, json
def read(): return json.loads(sys.stdin.readline())
def write(m): sys.stdout.write(json.dumps(m)+"\\n"); sys.stdout.flush()
req = read()
write({{"jsonrpc":"2.0","id":req["id"],"result":{{"protocolVersion":1,"agentCapabilities":{{}},"agentInfo":{{"name":"{name}","title":"{name}","version":"0"}},"authMethods":[]}}}})
req = read()
assert req["method"] == "session/new"
write({{"jsonrpc":"2.0","id":req["id"],"result":{{"sessionId":"{session_id}"}}}})
""")
    return script


def test_switch_between_agents(tmp_path):
    """US-ACP-005 AC-1: Connect to two agents and switch between them."""
    alpha_script = make_agent_script(tmp_path, "alpha", "sess_alpha")
    beta_script = make_agent_script(tmp_path, "beta", "sess_beta")

    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(name="alpha", transport=AgentTransport.LOCAL, command="python", args=[str(alpha_script)]))
    registry.add(AgentConfig(name="beta", transport=AgentTransport.LOCAL, command="python", args=[str(beta_script)]))

    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    sid_a = manager.connect("alpha")
    assert sid_a == "sess_alpha"
    assert manager.active_session_id() == "sess_alpha"

    sid_b = manager.connect("beta")
    assert sid_b == "sess_beta"
    assert manager.active_session_id() == "sess_beta"

    manager.switch_to("alpha")
    assert manager.active_session_id() == "sess_alpha"


def test_agent_not_found_error(tmp_path):
    """US-ACP-001 AC-2 + USE-002: Clear error when agent binary not found."""
    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(
        name="missing",
        transport=AgentTransport.LOCAL,
        command="nonexistent-binary-xyz",
        args=[],
    ))

    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    with pytest.raises(AcpConnectionError, match="not found"):
        manager.connect("missing")


def test_agent_crash_isolated(tmp_path):
    """AVAIL-002: Crash of one agent does not crash aede or affect other sessions."""
    stable_script = make_agent_script(tmp_path, "stable", "sess_stable")

    crash_script = tmp_path / "crash_agent.py"
    crash_script.write_text("import sys; sys.exit(1)")

    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(name="stable", transport=AgentTransport.LOCAL, command="python", args=[str(stable_script)]))
    registry.add(AgentConfig(name="crash", transport=AgentTransport.LOCAL, command="python", args=[str(crash_script)]))

    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    sid_stable = manager.connect("stable")
    assert sid_stable == "sess_stable"

    with pytest.raises(AcpConnectionError, match="crash"):
        manager.connect("crash")

    assert manager.active_session_id() == "sess_stable"


def test_connect_unknown_agent(tmp_path):
    """Connecting to an unregistered agent raises KeyError."""
    registry = AgentRegistry(config_dir=tmp_path)
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    with pytest.raises(KeyError, match="not found"):
        manager.connect("unknown")


def test_switch_to_not_connected(tmp_path):
    """Switching to an agent that has no active connection raises KeyError."""
    registry = AgentRegistry(config_dir=tmp_path)
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    with pytest.raises(KeyError, match="Not connected"):
        manager.switch_to("never-connected")


def test_list_connected_agents(tmp_path):
    """List which agents currently have active connections."""
    alpha_script = make_agent_script(tmp_path, "alpha", "sess_alpha")
    beta_script = make_agent_script(tmp_path, "beta", "sess_beta")

    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(name="alpha", transport=AgentTransport.LOCAL, command="python", args=[str(alpha_script)]))
    registry.add(AgentConfig(name="beta", transport=AgentTransport.LOCAL, command="python", args=[str(beta_script)]))

    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    assert manager.list_connected() == []

    manager.connect("alpha")
    assert manager.list_connected() == ["alpha"]

    manager.connect("beta")
    assert set(manager.list_connected()) == {"alpha", "beta"}
