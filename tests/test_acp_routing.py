"""Tests for ACP chat routing — AcpClient text accumulation, AcpProvider, and model detection."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aede.acp.client import AcpClient
from aede.acp.session import AcpSession, PromptResult
from aede.acp.registry import AgentConfig, AgentTransport


# ---------------------------------------------------------------------------
# Task 1: AcpClient accumulates agent_message_chunk text
# ---------------------------------------------------------------------------

def _make_chunk_agent(tmp_path: Path, chunks: list[str] | None = None) -> Path:
    """Create a fake agent that streams agent_message_chunk notifications."""
    if chunks is None:
        chunks = ["Hello ", "world"]
    script = tmp_path / "chunk_agent.py"
    chunk_json = json.dumps(chunks)
    script.write_text(f"""
import sys, json

def read():
    return json.loads(sys.stdin.readline())

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

chunks = {chunk_json}

# initialize
req = read()
write({{"jsonrpc":"2.0","id":req["id"],"result":{{"protocolVersion":1,"agentCapabilities":{{}},"agentInfo":{{"name":"chunk","title":"C","version":"0"}},"authMethods":[]}}}})

# session/new
req = read()
write({{"jsonrpc":"2.0","id":req["id"],"result":{{"sessionId":"sess_c"}}}})

# session/prompt
req = read()
for i, chunk in enumerate(chunks):
    write({{"jsonrpc":"2.0","method":"session/update","params":{{"sessionId":"sess_c","update":{{"sessionUpdate":"agent_message_chunk","messageId":"msg_1","content":{{"type":"text","text":chunk}}}}}}}})

write({{"jsonrpc":"2.0","id":req["id"],"result":{{"stopReason":"end_turn"}}}})
""")
    return script


def test_prompt_result_has_text_field():
    """PromptResult dataclass should have a text field."""
    result = PromptResult(stop_reason="end_turn", text="hello", raw={})
    assert result.text == "hello"
    assert result.stop_reason == "end_turn"


def test_prompt_accumulates_message_chunks(tmp_path):
    """AcpClient.prompt() should return accumulated text from agent_message_chunk notifications."""
    script = _make_chunk_agent(tmp_path, ["Hello ", "world"])
    config = AgentConfig(name="c", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()
    session = AcpSession(client)
    session.create(cwd=str(tmp_path))
    result = session.prompt("test")
    assert result.text == "Hello world"
    assert result.stop_reason == "end_turn"


def test_prompt_no_chunks_returns_empty_text(tmp_path):
    """When agent sends no message chunks, text should be empty string."""
    script = tmp_path / "no_chunk_agent.py"
    script.write_text("""
import sys, json

def read():
    return json.loads(sys.stdin.readline())

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentCapabilities":{},"agentInfo":{"name":"nochunk","title":"N","version":"0"},"authMethods":[]}})

req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"sess_nc"}})

req = read()
# no chunks, just respond
write({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}})
""")
    config = AgentConfig(name="nochunk", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()
    session = AcpSession(client)
    session.create(cwd=str(tmp_path))
    result = session.prompt("test")
    assert result.text == ""
    assert result.stop_reason == "end_turn"


def test_prompt_multiple_chunks_concatenated(tmp_path):
    """Multiple chunks should be concatenated in order."""
    script = _make_chunk_agent(tmp_path, ["a", "b", "c", "d"])
    config = AgentConfig(name="multi", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    client.initialize()
    session = AcpSession(client)
    session.create(cwd=str(tmp_path))
    result = session.prompt("test")
    assert result.text == "abcd"


# ---------------------------------------------------------------------------
# Task 2: Clean up ACP_COMMANDS — remove Agy, fix Gemini args
# ---------------------------------------------------------------------------

def test_acp_commands_no_agy():
    from aede.commands import ACP_COMMANDS
    assert "agy" not in ACP_COMMANDS


def test_acp_commands_gemini_uses_acp_flag():
    from aede.commands import ACP_COMMANDS
    assert ACP_COMMANDS["gemini"] == ("gemini", ["--acp"])


def test_model_presets_no_agy():
    from aede.models import MODEL_PRESETS
    assert "agy" not in MODEL_PRESETS


def test_server_acp_commands_match_cli():
    """Server ACP_COMMANDS should match commands.py ACP_COMMANDS."""
    from aede.commands import ACP_COMMANDS as cli_cmds
    from aede.server import ACP_COMMANDS as srv_cmds
    assert cli_cmds == srv_cmds


def test_acp_commands_includes_common_agents():
    from aede.commands import ACP_COMMANDS
    for name in ["codex", "claude-code", "gemini", "cline", "cursor", "goose", "opencode"]:
        assert name in ACP_COMMANDS, f"{name} missing from ACP_COMMANDS"


def test_model_presets_includes_acp_agents():
    from aede.models import MODEL_PRESETS
    for name in ["codex", "claude-code", "gemini", "cline", "cursor", "goose", "opencode"]:
        assert name in MODEL_PRESETS, f"{name} missing from MODEL_PRESETS"
        assert len(MODEL_PRESETS[name]) > 0, f"{name} has no presets"


# ---------------------------------------------------------------------------
# Task 3: AcpProvider
# ---------------------------------------------------------------------------

def test_acp_model_ids_set():
    """ACP_MODEL_IDS should include all known ACP agents."""
    from aede.provider import ACP_MODEL_IDS
    for name in ["codex", "claude-code", "gemini", "cline", "cursor", "goose", "opencode"]:
        assert name in ACP_MODEL_IDS, f"{name} missing from ACP_MODEL_IDS"


def test_get_provider_returns_acp_provider_for_acp_model():
    """get_provider should return AcpProvider when model is in ACP_MODEL_IDS."""
    from aede.provider import get_provider, AcpProvider
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.model = "codex"
    cfg.api_base_url = None
    manager = MagicMock()
    result = get_provider(cfg, acp_manager=manager)
    assert isinstance(result, AcpProvider)


def test_acp_provider_auto_connects():
    """AcpProvider.stream_turn should auto-connect if not already connected."""
    import asyncio
    from aede.provider import AcpProvider, NormalizedResponse
    from unittest.mock import MagicMock, AsyncMock
    manager = MagicMock()
    manager.list_connected.return_value = []
    manager.connect.return_value = "sess_1"
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "Hello from ACP"
    mock_result.stop_reason = "end_turn"
    mock_session.session.prompt.return_value = mock_result
    manager.active_session.return_value = mock_session

    provider = AcpProvider(model="codex", acp_manager=manager)
    console = MagicMock()
    resp = asyncio.get_event_loop().run_until_complete(
        provider.stream_turn(
            model="codex", system="sys", tools=[],
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1000, console=console,
        )
    )
    assert isinstance(resp, NormalizedResponse)
    assert resp.text == "Hello from ACP"
    manager.connect.assert_called_once_with("codex")


def test_acp_provider_reconnects_on_model_change():
    """Switching ACP models should disconnect old and connect new."""
    import asyncio
    from aede.provider import AcpProvider
    from unittest.mock import MagicMock
    manager = MagicMock()
    manager.list_connected.return_value = ["codex"]
    manager.connect.return_value = "sess_2"
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "response"
    mock_result.stop_reason = "end_turn"
    mock_session.session.prompt.return_value = mock_result
    manager.active_session.return_value = mock_session

    provider = AcpProvider(model="codex", acp_manager=manager)
    provider._current_agent = "codex"  # simulate already connected to codex
    console = MagicMock()
    asyncio.get_event_loop().run_until_complete(
        provider.stream_turn(
            model="claude-code", system="sys", tools=[],
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1000, console=console,
        )
    )
    manager.disconnect.assert_called_once_with("codex")
    manager.connect.assert_called_once_with("claude-code")


def test_acp_provider_cloud_auth_stub():
    """AcpProvider should accept credential_provider for cloud agents."""
    from aede.provider import AcpProvider
    from unittest.mock import MagicMock
    manager = MagicMock()
    cred = MagicMock()
    provider = AcpProvider(model="codex", acp_manager=manager, credential_provider=cred)
    assert provider._credential_provider is cred


# ---------------------------------------------------------------------------
# Task 4: Thread acp_manager through AgentLoop
# ---------------------------------------------------------------------------

def test_agent_loop_passes_acp_manager():
    from aede.agent import AgentLoop
    from unittest.mock import MagicMock, patch
    cfg = MagicMock()
    cfg.model = "codex"
    cfg.api_base_url = None
    cfg.home = MagicMock()
    cfg.data_dir = MagicMock()
    cfg.shell = "powershell"
    cfg.wsl_distro = ""
    cfg.tool_output_max_tokens = 8000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.85
    manager = MagicMock()
    agent = AgentLoop(
        cfg=cfg, session=MagicMock(), db=MagicMock(),
        rollout=MagicMock(), router=MagicMock(), gate_store=MagicMock(),
        tracker=MagicMock(), console=MagicMock(), project_dir=MagicMock(),
        acp_manager=manager,
    )
    with patch("aede.provider.get_provider") as mock_get:
        mock_get.return_value = MagicMock()
        agent._get_provider()
        _, kwargs = mock_get.call_args
        assert kwargs.get("acp_manager") is manager


def test_agent_loop_default_acp_manager_none():
    """AgentLoop should default acp_manager to None (backward compat)."""
    from aede.agent import AgentLoop
    from unittest.mock import MagicMock, patch
    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-6"
    cfg.api_base_url = None
    cfg.home = MagicMock()
    cfg.data_dir = MagicMock()
    cfg.shell = "powershell"
    cfg.wsl_distro = ""
    cfg.tool_output_max_tokens = 8000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.85
    agent = AgentLoop(
        cfg=cfg, session=MagicMock(), db=MagicMock(),
        rollout=MagicMock(), router=MagicMock(), gate_store=MagicMock(),
        tracker=MagicMock(), console=MagicMock(), project_dir=MagicMock(),
    )
    assert agent._acp_manager is None
    with patch("aede.provider.get_provider") as mock_get:
        mock_get.return_value = MagicMock()
        agent._get_provider()
        _, kwargs = mock_get.call_args
        assert kwargs.get("acp_manager") is None


# ---------------------------------------------------------------------------
# Tasks 5+8: CLI + Server
# ---------------------------------------------------------------------------

def test_cli_no_acp_active_flag():
    """CLI should not have acp_active flag or routing block."""
    from pathlib import Path
    src = Path("aede/cli.py").read_text()
    assert "acp_active" not in src


def test_cli_passes_acp_manager_to_agent():
    from pathlib import Path
    src = Path("aede/cli.py").read_text()
    assert "acp_manager=acp_manager" in src


def test_server_websocket_passes_acp_manager():
    from pathlib import Path
    src = Path("aede/server.py").read_text()
    assert "acp_manager=" in src
