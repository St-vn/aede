import json
import pytest
from pathlib import Path
from aede.acp.client import AcpClient
from aede.acp.session import AcpSession, PromptResult
from aede.acp.registry import AgentConfig, AgentTransport


def make_session_agent(tmp_path: Path) -> Path:
    """Create a fake agent that handles initialize + session/new + session/prompt with streaming."""
    script = tmp_path / "session_agent.py"
    script.write_text("""
import sys, json

def read():
    return json.loads(sys.stdin.readline())

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

# initialize
req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentCapabilities":{},"agentInfo":{"name":"fake","title":"Fake Agent","version":"0"},"authMethods":[]}})

# session/new
req = read()
assert req["method"] == "session/new"
write({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"sess_001"}})

# session/prompt
req = read()
assert req["method"] == "session/prompt"

# stream text update before responding
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_001","update":{"sessionUpdate":"agent_message_chunk","messageId":"msg_1","content":{"type":"text","text":"Hello from fake agent"}}}})

# respond to session/prompt
write({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}})
""")
    return script


def test_session_create_and_prompt(tmp_path):
    """US-ACP-001 AC-1 + US-ACP-004 AC-1: Create session and receive streamed text updates."""
    script = make_session_agent(tmp_path)
    config = AgentConfig(name="fake", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()

    session = AcpSession(client)
    session_id = session.create(cwd=str(tmp_path))

    updates = []
    result = session.prompt("Hello", on_update=lambda u: updates.append(u))

    assert session_id == "sess_001"
    assert result.stop_reason == "end_turn"
    assert len(updates) == 1
    assert updates[0]["sessionUpdate"] == "agent_message_chunk"
    assert updates[0]["content"]["text"] == "Hello from fake agent"


def test_session_prompt_empty_response(tmp_path):
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
    client.initialize()

    session = AcpSession(client)
    session.create(cwd=str(tmp_path))

    updates = []
    result = session.prompt("Hi", on_update=lambda u: updates.append(u))

    assert result.stop_reason == "end_turn"
    assert len(updates) == 0


def test_session_prompt_with_tool_call(tmp_path):
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
# stream tool call before responding
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_tool","update":{"sessionUpdate":"tool_call","toolCallId":"call_001","title":"Reading file","kind":"read","status":"pending"}}})
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_tool","update":{"sessionUpdate":"tool_call_update","toolCallId":"call_001","status":"in_progress"}}})
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_tool","update":{"sessionUpdate":"tool_call_update","toolCallId":"call_001","status":"completed"}}})
write({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}})
""")
    config = AgentConfig(name="tool", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()

    session = AcpSession(client)
    session.create(cwd=str(tmp_path))

    updates = []
    result = session.prompt("Read the file", on_update=lambda u: updates.append(u))

    assert result.stop_reason == "end_turn"
    tool_updates = [u for u in updates if u["sessionUpdate"] == "tool_call"]
    assert len(tool_updates) == 1
    assert tool_updates[0]["toolCallId"] == "call_001"
