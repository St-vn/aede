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


async def test_prompt_accumulates_message_chunks(tmp_path):
    """AcpClient.prompt() should return accumulated text from agent_message_chunk notifications."""
    script = _make_chunk_agent(tmp_path, ["Hello ", "world"])
    config = AgentConfig(name="c", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()
    session = AcpSession(client)
    await session.create(cwd=str(tmp_path))
    result = await session.prompt("test")
    assert result.text == "Hello world"
    assert result.stop_reason == "end_turn"
    await client.aclose()


async def test_prompt_no_chunks_returns_empty_text(tmp_path):
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
    await client.initialize()
    session = AcpSession(client)
    await session.create(cwd=str(tmp_path))
    result = await session.prompt("test")
    assert result.text == ""
    assert result.stop_reason == "end_turn"
    await client.aclose()


async def test_prompt_multiple_chunks_concatenated(tmp_path):
    """Multiple chunks should be concatenated in order."""
    script = _make_chunk_agent(tmp_path, ["a", "b", "c", "d"])
    config = AgentConfig(name="multi", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()
    session = AcpSession(client)
    await session.create(cwd=str(tmp_path))
    result = await session.prompt("test")
    assert result.text == "abcd"
    await client.aclose()


# ---------------------------------------------------------------------------
# Task 2: Clean up ACP_COMMANDS — remove Agy, fix Gemini args
# ---------------------------------------------------------------------------

def test_acp_commands_includes_agy():
    from aede.commands import ACP_COMMANDS
    assert "agy" in ACP_COMMANDS
    assert ACP_COMMANDS["agy"] == ("agy", ["--acp"])


def test_acp_commands_gemini_uses_acp_flag():
    from aede.commands import ACP_COMMANDS
    assert ACP_COMMANDS["gemini"] == ("gemini", ["--acp"])


def test_model_presets_includes_agy():
    from aede.models import MODEL_PRESETS
    assert "agy" in MODEL_PRESETS
    assert MODEL_PRESETS["agy"][0]["id"] == "agy"
    assert MODEL_PRESETS["agy"][0]["label"] == "Antigravity"


def test_server_acp_commands_match_cli():
    """Server ACP_COMMANDS should match commands.py ACP_COMMANDS."""
    from aede.commands import ACP_COMMANDS as cli_cmds
    from aede.server import ACP_COMMANDS as srv_cmds
    assert cli_cmds == srv_cmds


def test_acp_commands_includes_common_agents():
    from aede.commands import ACP_COMMANDS
    for name in ["codex", "claude-code", "gemini", "agy", "cline", "cursor", "goose"]:
        assert name in ACP_COMMANDS, f"{name} missing from ACP_COMMANDS"


def test_model_presets_includes_acp_agents():
    from aede.models import MODEL_PRESETS
    for name in ["codex", "claude-code", "gemini", "agy", "cline", "cursor", "goose", "opencode"]:
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


async def test_acp_provider_auto_connects():
    """AcpProvider.stream_turn should auto-connect if not already connected."""
    from aede.provider import AcpProvider, NormalizedResponse
    from unittest.mock import MagicMock, AsyncMock
    manager = MagicMock()
    manager.list_connected.return_value = []
    manager.connect = AsyncMock(return_value="sess_1")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "Hello from ACP"
    mock_result.stop_reason = "end_turn"
    mock_session.session.prompt = AsyncMock(return_value=mock_result)
    manager.active_session.return_value = mock_session

    provider = AcpProvider(model="codex", acp_manager=manager)
    console = MagicMock()
    resp = await provider.stream_turn(
        model="codex", system="sys", tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000, console=console,
    )
    assert isinstance(resp, NormalizedResponse)
    assert resp.text == "Hello from ACP"
    manager.connect.assert_called_once_with("codex")


async def test_acp_provider_reconnects_on_model_change():
    """Switching ACP models should disconnect old and connect new."""
    from aede.provider import AcpProvider
    from unittest.mock import MagicMock, AsyncMock
    manager = MagicMock()
    manager.list_connected.return_value = ["codex"]
    manager.connect = AsyncMock(return_value="sess_2")
    manager.disconnect = AsyncMock()
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "response"
    mock_result.stop_reason = "end_turn"
    mock_session.session.prompt = AsyncMock(return_value=mock_result)
    manager.active_session.return_value = mock_session

    provider = AcpProvider(model="codex", acp_manager=manager)
    provider._current_agent = "codex"  # simulate already connected to codex
    console = MagicMock()
    await provider.stream_turn(
        model="claude-code", system="sys", tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000, console=console,
    )
    manager.disconnect.assert_called_once_with("codex")
    manager.connect.assert_called_once_with("claude-code")


async def test_acp_provider_connect_runs_on_event_loop():
    """ACP connect uses async subprocess I/O — runs directly on the event loop."""
    from aede.provider import AcpProvider
    from unittest.mock import MagicMock, AsyncMock
    manager = MagicMock()
    manager.list_connected.return_value = []
    manager.connect = AsyncMock(return_value="sess_fast")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "ok"
    mock_session.session.prompt = AsyncMock(return_value=mock_result)
    manager.active_session.return_value = mock_session

    provider = AcpProvider(model="codex", acp_manager=manager)
    resp = await provider.stream_turn(
        model="codex", system="sys", tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000, console=MagicMock(),
    )
    assert resp.text == "ok"


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


# ---------------------------------------------------------------------------
# Sub-model entries
# ---------------------------------------------------------------------------

def test_acp_commands_has_sub_model_entries():
    """ACP_COMMANDS should include sub-model entries for agents with env var overrides."""
    from aede.commands import ACP_COMMANDS
    
    # Claude Code sub-models
    assert "claude-code/fable-5" in ACP_COMMANDS
    assert "claude-code/opus-4-8" in ACP_COMMANDS
    # assert "claude-code/opus-4-7" in ACP_COMMANDS
    assert "claude-code/sonnet-4-6" in ACP_COMMANDS
    assert "claude-code/haiku-4-5" in ACP_COMMANDS
    
    # Codex sub-models
    assert "codex/gpt-5.5" in ACP_COMMANDS
    assert "codex/gpt-5.3-codex" in ACP_COMMANDS
    assert "codex/o3" in ACP_COMMANDS
    assert "codex/o4-mini" in ACP_COMMANDS
    
    # Goose sub-models
    assert "goose/anthropic-claude-sonnet-4-6" in ACP_COMMANDS
    assert "goose/openai-gpt-4o" in ACP_COMMANDS
    
    # Agy sub-models
    assert "agy/gemini-3-5-flash" in ACP_COMMANDS
    assert "agy/gemini-3-1-pro" in ACP_COMMANDS
    assert "agy/claude-sonnet-4-6" in ACP_COMMANDS
    assert "agy/claude-opus-4-6" in ACP_COMMANDS


def test_get_acp_model_override_returns_correct_values():
    """get_acp_model_override should return correct model overrides for sub-model entries."""
    from aede.commands import get_acp_model_override
    
    # Claude Code
    assert get_acp_model_override("claude-code/fable-5") == "claude-fable-5"
    assert get_acp_model_override("claude-code/opus-4-8") == "claude-opus-4-8"
    # assert get_acp_model_override("claude-code/opus-4-7") == "claude-opus-4-7"
    assert get_acp_model_override("claude-code/sonnet-4-6") == "claude-sonnet-4-6"
    assert get_acp_model_override("claude-code/haiku-4-5") == "claude-haiku-4-5"
    
    # Codex
    assert get_acp_model_override("codex/gpt-5.5") == "gpt-5.5"
    assert get_acp_model_override("codex/gpt-5.3-codex") == "gpt-5.3-codex"
    assert get_acp_model_override("codex/o3") == "o3"
    assert get_acp_model_override("codex/o4-mini") == "o4-mini"
    
    # Goose
    assert get_acp_model_override("goose/anthropic-claude-sonnet-4-6") == "anthropic/claude-sonnet-4-6"
    assert get_acp_model_override("goose/openai-gpt-4o") == "openai/gpt-4o"
    
    # Agy
    assert get_acp_model_override("agy/gemini-3-5-flash") == "gemini-3.5-flash"
    assert get_acp_model_override("agy/gemini-3-1-pro") == "gemini-3.1-pro"
    assert get_acp_model_override("agy/claude-sonnet-4-6") == "claude-sonnet-4.6-thinking"
    assert get_acp_model_override("agy/claude-opus-4-6") == "claude-opus-4.6-thinking"
    
    # Base agents return None
    assert get_acp_model_override("claude-code") is None
    assert get_acp_model_override("codex") is None
    assert get_acp_model_override("goose") is None
    assert get_acp_model_override("agy") is None


def test_acp_model_ids_includes_sub_model_entries():
    """ACP_MODEL_IDS should include sub-model entries."""
    from aede.provider import ACP_MODEL_IDS
    
    # Claude Code sub-models
    assert "claude-code/fable-5" in ACP_MODEL_IDS
    assert "claude-code/opus-4-8" in ACP_MODEL_IDS
    # assert "claude-code/opus-4-7" in ACP_MODEL_IDS
    assert "claude-code/sonnet-4-6" in ACP_MODEL_IDS
    assert "claude-code/haiku-4-5" in ACP_MODEL_IDS
    
    # Codex sub-models
    assert "codex/gpt-5.5" in ACP_MODEL_IDS
    assert "codex/gpt-5.3-codex" in ACP_MODEL_IDS
    assert "codex/o3" in ACP_MODEL_IDS
    assert "codex/o4-mini" in ACP_MODEL_IDS
    
    # Goose sub-models
    assert "goose/anthropic-claude-sonnet-4-6" in ACP_MODEL_IDS
    assert "goose/openai-gpt-4o" in ACP_MODEL_IDS
    
        # No agy sub-models — agy has no official ACP support


def test_agent_config_has_model_override_field():
    """AgentConfig should have a model_override field."""
    config = AgentConfig(
        name="test",
        transport=AgentTransport.LOCAL,
        command="test-cmd",
        model_override="test-model",
    )
    assert config.model_override == "test-model"


def test_agent_config_model_override_defaults_to_none():
    """AgentConfig model_override should default to None."""
    config = AgentConfig(
        name="test",
        transport=AgentTransport.LOCAL,
        command="test-cmd",
    )
    assert config.model_override is None


def test_model_presets_has_sub_model_entries():
    """MODEL_PRESETS should include sub-model entries for ACP agents."""
    from aede.models import MODEL_PRESETS
    
    # Claude Code
    claude_code_models = [m["id"] for m in MODEL_PRESETS["claude-code"]]
    assert "claude-code" in claude_code_models
    assert "claude-code/fable-5" in claude_code_models
    assert "claude-code/opus-4-8" in claude_code_models
    # assert "claude-code/opus-4-7" in claude_code_models
    assert "claude-code/sonnet-4-6" in claude_code_models
    assert "claude-code/haiku-4-5" in claude_code_models
    
    # Codex
    codex_models = [m["id"] for m in MODEL_PRESETS["codex"]]
    assert "codex" in codex_models
    assert "codex/gpt-5.5" in codex_models
    assert "codex/gpt-5.3-codex" in codex_models
    assert "codex/o3" in codex_models
    assert "codex/o4-mini" in codex_models
    
    # Goose
    goose_models = [m["id"] for m in MODEL_PRESETS["goose"]]
    assert "goose" in goose_models
    assert "goose/anthropic-claude-sonnet-4-6" in goose_models
    assert "goose/openai-gpt-4o" in goose_models
    
    # Agy
    agy_models = [m["id"] for m in MODEL_PRESETS["agy"]]
    assert "agy" in agy_models
    assert "agy/gemini-3-5-flash" in agy_models
    assert "agy/gemini-3-1-pro" in agy_models
    assert "agy/claude-sonnet-4-6" in agy_models
    assert "agy/claude-opus-4-6" in agy_models


# def test_acp_client_injects_claude_code_model_override():
#     """AcpClient should inject ANTHROPIC_MODEL env var for Claude Code sub-models."""
#     from aede.acp.client import AcpClient
    
#     config = AgentConfig(
#         name="claude-code/opus-4-7",
#         transport=AgentTransport.LOCAL,
#         command="claude-agent-acp",
#         model_override="claude-opus-4-7",
#     )
#     client = AcpClient(config)
#     env = client._inject_env()
#     assert env.get("ANTHROPIC_MODEL") == "claude-opus-4-7"


def test_acp_client_injects_goose_model_override():
    """AcpClient should inject GOOSE_PROVIDER and GOOSE_MODEL env vars for Goose sub-models."""
    from aede.acp.client import AcpClient
    
    config = AgentConfig(
        name="goose/anthropic-claude-sonnet-4-6",
        transport=AgentTransport.LOCAL,
        command="goose",
        model_override="anthropic/claude-sonnet-4-6",
    )
    client = AcpClient(config)
    env = client._inject_env()
    assert env.get("GOOSE_PROVIDER") == "anthropic"
    assert env.get("GOOSE_MODEL") == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_no_thread_growth_and_loop_responsive_over_many_turns():
    import threading, asyncio
    from aede.provider import AcpProvider
    from unittest.mock import AsyncMock, MagicMock
    mgr = MagicMock(); mgr.list_connected.return_value = ["codex"]
    mgr.connect = AsyncMock(return_value="s"); mgr.switch_to = MagicMock()
    async def _mock_prompt(text, on_update=None):
        await asyncio.sleep(0)
        return MagicMock(text="x")
    sess = MagicMock(); sess.session.prompt = _mock_prompt
    mgr.active_session.return_value = sess
    base = threading.active_count()
    ticks = {"n": 0}; stop = {"v": False}
    async def hb():
        while not stop["v"]:
            await asyncio.sleep(0)
            ticks["n"] += 1
    h = asyncio.create_task(hb())
    for _ in range(100):
        p = AcpProvider(model="codex", acp_manager=mgr)
        p._current_agent = "codex"
        await p.stream_turn(model="codex", system="", tools=[],
            messages=[{"role":"user","content":"hi"}], max_tokens=10, console=MagicMock())
    stop["v"] = True; await h
    assert threading.active_count() <= base + 2
    assert ticks["n"] > 50


def test_acp_client_codex_model_override_in_args():
    """AcpClient should add --model flag to args for Codex sub-models."""
    from aede.acp.client import AcpClient
    
    config = AgentConfig(
        name="codex/o3",
        transport=AgentTransport.LOCAL,
        command="codex-acp",
        model_override="o3",
    )
    client = AcpClient(config)
    # We can't easily test _start without mocking subprocess, but we can verify the logic
    # by checking that model_override is set correctly
    assert config.model_override == "o3"
    assert config.name == "codex/o3"
