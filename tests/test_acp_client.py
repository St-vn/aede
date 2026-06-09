import json
import pytest
from pathlib import Path
from aede.acp.client import AcpClient
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
