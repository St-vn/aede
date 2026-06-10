import pytest
from pathlib import Path
from unittest.mock import MagicMock
from aede.acp.client import AcpClient, AcpError
from aede.acp.session import AcpSession, PromptResult
from aede.acp.registry import AgentConfig, AgentTransport


def make_session_agent(script_path: Path) -> Path:
    """Fake ACP agent that responds to initialize + session/new + prompt."""
    script_path.write_text("""
import sys, json

def read():
    return json.loads(sys.stdin.readline())

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentCapabilities":{},"agentInfo":{"name":"fake","title":"Fake Agent","version":"0"},"authMethods":[]}})

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"sess_001"}})

req = read()
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_001","update":{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"Hello from fake agent"}}}})
write({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}})
""")
    return script_path


async def test_session_create_and_prompt(tmp_path):
    """US-ACP-001 AC-1 + US-ACP-004 AC-1: Create session and receive streamed text updates."""
    script = make_session_agent(tmp_path / "fake_agent.py")
    config = AgentConfig(name="fake", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()

    session = AcpSession(client)
    session_id = await session.create(cwd=str(tmp_path))

    updates = []
    result = await session.prompt("Hello", on_update=lambda u: updates.append(u))

    assert session_id == "sess_001"
    assert result.stop_reason == "end_turn"
    assert len(updates) == 1
    assert updates[0]["sessionUpdate"] == "agent_message_chunk"
    assert updates[0]["content"]["text"] == "Hello from fake agent"
    await client.aclose()


async def test_session_prompt_empty_response(tmp_path):
    """US-ACP-004 AC-3: Agent responds with stop_reason but no content updates."""
    script = tmp_path / "empty_agent.py"
    script.write_text("""
import sys, json

def read():
    return json.loads(sys.stdin.readline())

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentCapabilities":{},"agentInfo":{"name":"empty","title":"Empty","version":"0"},"authMethods":[]}})

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"sess_empty"}})

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}})
""")
    config = AgentConfig(name="empty", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()

    session = AcpSession(client)
    await session.create(cwd=str(tmp_path))

    updates = []
    result = await session.prompt("Hi", on_update=lambda u: updates.append(u))

    assert result.stop_reason == "end_turn"
    assert len(updates) == 0
    await client.aclose()


async def test_session_prompt_with_tool_call(tmp_path):
    """US-ACP-004 AC-2: Agent streams tool call updates during prompt turn."""
    script = tmp_path / "tool_agent.py"
    script.write_text("""
import sys, json

def read():
    return json.loads(sys.stdin.readline())

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentCapabilities":{},"agentInfo":{"name":"tool","title":"Tool","version":"0"},"authMethods":[]}})

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"sess_tool"}})

req = read()
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_tool","update":{"sessionUpdate":"tool_call","toolCallId":"call_001","title":"Reading file","kind":"read","status":"pending"}}})
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_tool","update":{"sessionUpdate":"tool_call_update","toolCallId":"call_001","status":"in_progress"}}})
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_tool","update":{"sessionUpdate":"tool_call_update","toolCallId":"call_001","status":"completed"}}})
write({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}})
""")
    config = AgentConfig(name="tool", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()

    session = AcpSession(client)
    await session.create(cwd=str(tmp_path))

    updates = []
    result = await session.prompt("Read the file", on_update=lambda u: updates.append(u))

    assert result.stop_reason == "end_turn"
    tool_updates = [u for u in updates if u["sessionUpdate"] == "tool_call"]
    assert len(tool_updates) == 1
    assert tool_updates[0]["toolCallId"] == "call_001"
    await client.aclose()
