import json
import os
import pytest
from pathlib import Path
from aede.acp.client import AcpClient
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
