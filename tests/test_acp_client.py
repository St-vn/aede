import inspect
import json
import os
import pytest
from pathlib import Path
from aede.acp.client import AcpClient, AcpError
from aede.acp.credentials import CredentialProvider
from aede.acp.registry import AgentConfig, AgentTransport


def make_echo_agent(script_path: Path) -> Path:
    """Create a fake ACP agent that echoes JSON-RPC requests for testing."""
    script_path.write_text("""
import sys, json

def read():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
assert req["method"] == "initialize"
write({
    "jsonrpc": "2.0",
    "id": req["id"],
    "result": {
        "protocolVersion": 1,
        "agentCapabilities": {"loadSession": False},
        "agentInfo": {"name": "echo", "title": "Echo Agent", "version": "0.0.0"},
        "authMethods": [],
    },
})
""")
    return script_path


def test_initialize_handshake(tmp_path):
    """US-ACP-001 AC-1: Spawn agent and complete the initialize handshake."""
    script = make_echo_agent(tmp_path / "echo_agent.py")
    config = AgentConfig(
        name="echo",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(script)],
    )

    client = AcpClient(config)
    result = client.initialize()

    assert result.protocol_version == 1
    assert result.agent_info.name == "echo"


def test_initialize_protocol_mismatch(tmp_path):
    """US-ACP-001 AC-3: Agent that returns an incompatible protocol version."""
    script = tmp_path / "bad_agent.py"
    script.write_text("""
import sys, json
line = sys.stdin.readline()
req = json.loads(line)
sys.stdout.write(json.dumps({
    "jsonrpc": "2.0",
    "id": req["id"],
    "result": {
        "protocolVersion": 999,
        "agentCapabilities": {},
        "agentInfo": {"name": "bad", "title": "Bad", "version": "0.0"},
        "authMethods": [],
    },
}) + "\\n")
sys.stdout.flush()
""")
    config = AgentConfig(name="bad", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    with pytest.raises(Exception, match="protocol version 999"):
        client.initialize()


def test_initialize_agent_error(tmp_path):
    """US-ACP-001 AC-3: Agent returns a JSON-RPC error during initialize."""
    script = tmp_path / "error_agent.py"
    script.write_text("""
import sys, json
line = sys.stdin.readline()
req = json.loads(line)
sys.stdout.write(json.dumps({
    "jsonrpc": "2.0",
    "id": req["id"],
    "error": {"code": -32000, "message": "Model unavailable"},
}) + "\\n")
sys.stdout.flush()
""")
    config = AgentConfig(name="err", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    with pytest.raises(Exception, match="Model unavailable"):
        client.initialize()


def make_env_echo_agent(script_path: Path) -> Path:
    """Create a fake ACP agent that reads an env var and returns it."""
    script_path.write_text(f"""
import sys, json, os

def read():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
assert req["method"] == "initialize"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
write({{
    "jsonrpc": "2.0",
    "id": req["id"],
    "result": {{
        "protocolVersion": 1,
        "agentCapabilities": {{"loadSession": False}},
        "agentInfo": {{"name": api_key, "title": "Env Agent", "version": "0.0.0"}},
        "authMethods": [],
    }},
}})
""")
    return script_path


def test_start_injects_credentials_ref_env(tmp_path):
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text(json.dumps({
        "ANTHROPIC_API_KEY": {"value": "sk-ant-test-key", "provider": "anthropic"},
    }))
    provider = CredentialProvider(home=tmp_path)
    script = make_env_echo_agent(tmp_path / "env_agent.py")
    config = AgentConfig(
        name="env_test",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(script)],
        credentials_ref="ANTHROPIC_API_KEY",
    )
    client = AcpClient(config)
    result = client.initialize(credential_provider=provider)
    assert result.agent_info.name == "sk-ant-test-key"


def test_start_with_unset_credentials_ref_skips_injection(tmp_path):
    provider = CredentialProvider(home=tmp_path)
    script = make_env_echo_agent(tmp_path / "no_ref_agent.py")
    config = AgentConfig(
        name="no_ref",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(script)],
        credentials_ref="MISSING_KEY",
    )
    client = AcpClient(config)
    result = client.initialize(credential_provider=provider)
    assert result.agent_info.name == ""


# ── new_session timeout + notification-skipping (regression for the
#    "Agent 'claude-code' timed out after 10.0s" bug) ──────────────────


def make_session_agent(script_path: Path, *, new_delay: float = 0.0,
                       notify_first: bool = False) -> Path:
    """Fake ACP agent: answers initialize, then session/new.

    ``new_delay`` sleeps before replying to session/new (to exercise the
    timeout).  ``notify_first`` emits an id-less session/update notification
    before the session/new response (to exercise notification-skipping).
    """
    script_path.write_text(f"""
import sys, json, time

def read():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
assert req["method"] == "initialize"
write({{
    "jsonrpc": "2.0", "id": req["id"],
    "result": {{
        "protocolVersion": 1,
        "agentCapabilities": {{"loadSession": False}},
        "agentInfo": {{"name": "sess", "title": "Sess", "version": "0.0.0"}},
        "authMethods": [],
    }},
}})

req2 = read()
assert req2["method"] == "session/new"
time.sleep({new_delay})
if {notify_first}:
    # id-less notification that must be skipped
    write({{"jsonrpc": "2.0", "method": "session/update",
            "params": {{"update": {{"sessionUpdate": "agent_thought"}}}}}})
write({{"jsonrpc": "2.0", "id": req2["id"], "result": {{"sessionId": "sess_42"}}}})
""")
    return script_path


def test_new_session_default_timeout_is_60s():
    """Guard: nobody silently lowers the new_session timeout back toward 10s."""
    assert inspect.signature(AcpClient.new_session).parameters["timeout"].default == 60.0


def test_new_session_succeeds(tmp_path):
    script = make_session_agent(tmp_path / "sess_agent.py")
    config = AgentConfig(name="sess", transport=AgentTransport.LOCAL,
                         command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()
    assert client.new_session(cwd="") == "sess_42"
    client.close()


def test_new_session_times_out_when_agent_slow(tmp_path):
    """A short explicit timeout must raise the 'timed out' AcpError."""
    script = make_session_agent(tmp_path / "slow_agent.py", new_delay=0.5)
    config = AgentConfig(name="sess", transport=AgentTransport.LOCAL,
                         command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()
    with pytest.raises(AcpError, match="timed out"):
        client.new_session(cwd="", timeout=0.05)
    client.close()


def test_new_session_skips_leading_notification(tmp_path):
    """An id-less notification before the response must be skipped, not crash."""
    script = make_session_agent(tmp_path / "notify_agent.py", notify_first=True)
    config = AgentConfig(name="sess", transport=AgentTransport.LOCAL,
                         command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()
    assert client.new_session(cwd="") == "sess_42"
    client.close()
