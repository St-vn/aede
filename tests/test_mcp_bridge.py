import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock


@pytest.fixture
def server_configs():
    from aede.mcp.client import MCPServerConfig
    return {
        "playwright": MCPServerConfig(
            command="npx", args=["-y", "@playwright/mcp"],
            env={}, trusted=True,
        ),
        "filesystem": MCPServerConfig(
            command="npx", args=["-y", "server-filesystem", "/tmp"],
            env={}, trusted=False,
        ),
    }


def test_bridge_init_creates_thread_and_loop(server_configs):
    """MCPBridge.__init__ creates a Thread with a new event loop in the daemon thread."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    assert bridge._thread is not None
    assert bridge._thread.daemon is True
    assert bridge._thread.is_alive()
    assert bridge._loop is not None


def test_bridge_thread_running(server_configs):
    """Bridge thread stays alive after creation."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    assert bridge._thread.is_alive()
    bridge.shutdown_all()
    bridge._thread.join(timeout=3)
    assert not bridge._thread.is_alive()


@pytest.mark.asyncio
async def test_spawn_one_success(server_configs):
    """_spawn_one spawns subprocess, initializes session, calls list_tools, returns schemas."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock()

    mock_tool = MagicMock()
    mock_tool.name = "navigate"
    mock_tool.description = "Navigate to URL"
    mock_tool.inputSchema = {"type": "object", "properties": {"url": {"type": "string"}}}
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

    mock_params = MagicMock()
    mock_read = MagicMock()
    mock_write = MagicMock()

    with patch("mcp.ClientSession", return_value=mock_session), \
         patch("mcp.StdioServerParameters", return_value=mock_params), \
         patch("mcp.client.stdio.stdio_client") as mock_stdio:

        mock_transport = MagicMock()
        mock_transport.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_transport.__aexit__ = AsyncMock()
        mock_stdio.return_value = mock_transport

        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        result = await bridge._spawn_one("playwright", server_configs["playwright"])

    assert "navigate" in [t["name"] for t in result]
    assert bridge._sessions.get("playwright") is not None


@pytest.mark.asyncio
async def test_spawn_one_session_stays_open(server_configs):
    """Session remains usable after _spawn_one returns (not closed by context exit)."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = ""
    mock_tool.inputSchema = {"type": "object"}
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

    mock_read = MagicMock()
    mock_write = MagicMock()

    with patch("mcp.ClientSession", return_value=mock_session), \
         patch("mcp.client.stdio.stdio_client") as mock_stdio, \
         patch("mcp.StdioServerParameters"):

        mock_transport = MagicMock()
        mock_transport.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
        mock_transport.__aexit__ = AsyncMock()
        mock_stdio.return_value = mock_transport

        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        await bridge._spawn_one("test_server", server_configs["playwright"])

    assert "test_server" in bridge._sessions
    mock_session.__aexit__.assert_not_called()


@pytest.mark.asyncio
async def test_spawn_one_timeout(server_configs):
    """Timeout during spawn via spawn_all returns server in failed list."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)

    async def slow_spawn(name, cfg):
        await asyncio.sleep(100)

    bridge._spawn_one = AsyncMock(side_effect=slow_spawn)

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        failures = bridge.spawn_all()

    assert "playwright" in failures


@pytest.mark.asyncio
async def test_spawn_all_concurrent(server_configs):
    """spawn_all calls _spawn_one for each server concurrently."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)

    async def fake_spawn(name, cfg):
        await asyncio.sleep(0.01)
        return [{"name": f"{name}_tool", "description": "", "input_schema": {}}]

    bridge._spawn_one = AsyncMock(side_effect=fake_spawn)
    failures = bridge.spawn_all()

    assert failures == []
    assert bridge._spawn_one.call_count == 2


@pytest.mark.asyncio
async def test_spawn_all_partial_failure(server_configs):
    """spawn_all returns list of failed server names on partial failure."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)

    async def fake_spawn(name, cfg):
        if name == "playwright":
            return [{"name": "tool1", "description": "", "input_schema": {}}]
        raise RuntimeError("Failed to spawn")

    bridge._spawn_one = AsyncMock(side_effect=fake_spawn)
    failures = bridge.spawn_all()

    assert failures == ["filesystem"]


@pytest.mark.asyncio
async def test_spawn_all_timeout_enforcement(server_configs):
    """spawn_all enforces per-server timeout via asyncio.wait_for."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)

    async def slow_spawn(name, cfg):
        await asyncio.sleep(100)

    bridge._spawn_one = AsyncMock(side_effect=slow_spawn)

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        failures = bridge.spawn_all()

    assert len(failures) == 2


@pytest.mark.asyncio
async def test_discovered_tools_format(server_configs):
    """discovered_tools() returns list[tuple[str, str, MCPServerConfig, dict]]."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    bridge._tool_schemas = {
        "playwright": [
            {"name": "navigate", "description": "Go to URL",
             "input_schema": {"type": "object"}},
        ],
    }

    tools = bridge.discovered_tools()
    assert len(tools) == 1
    name, server_name, cfg, schema = tools[0]
    assert name == "mcp__playwright__navigate"
    assert server_name == "playwright"
    assert cfg.trusted is True
    assert schema["name"] == "mcp__playwright__navigate"


@pytest.mark.asyncio
async def test_discovered_tools_naming(server_configs):
    """Tool names are prefixed with mcp__<server>__ per MCP convention."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    bridge._tool_schemas = {
        "playwright": [
            {"name": "goto", "description": "", "input_schema": {}},
        ],
    }

    tools = bridge.discovered_tools()
    assert tools[0][0] == "mcp__playwright__goto"


@pytest.mark.asyncio
async def test_discovered_tools_anthropic_schema(server_configs):
    """discovered_tools returns Anthropic-format schemas."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    bridge._tool_schemas = {
        "playwright": [
            {"name": "run", "description": "Run test",
             "input_schema": {"type": "object", "properties": {"cmd": {"type": "string"}}}},
        ],
    }

    tools = bridge.discovered_tools()
    assert len(tools) == 1
    _, _, _, schema = tools[0]
    assert schema["name"] == "mcp__playwright__run"
    assert "description" in schema
    assert "input_schema" in schema


@pytest.mark.asyncio
async def test_call_sync_success(server_configs):
    """call_sync submits to bridge loop, waits for result, extracts text."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "https://example.com"
    mock_content.type = "text"
    mock_result.content = [mock_content]
    mock_session.call_tool = AsyncMock(return_value=mock_result)
    bridge._sessions = {"playwright": mock_session}

    result = bridge.call_sync("playwright", "navigate", {"url": "https://example.com"})
    assert result == "https://example.com"


@pytest.mark.asyncio
async def test_call_sync_timeout(server_configs):
    """call_sync raises TimeoutError on timeout via run_coroutine_threadsafe."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    bridge._sessions = {"playwright": MagicMock()}

    mock_future = MagicMock()
    mock_future.result.side_effect = asyncio.TimeoutError

    with patch("asyncio.run_coroutine_threadsafe", return_value=mock_future):
        with pytest.raises(TimeoutError):
            bridge.call_sync("playwright", "navigate", {"url": "x"})


@pytest.mark.asyncio
async def test_call_sync_dead_server_error(server_configs):
    """call_sync raises RuntimeError when server is not running."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    bridge._sessions = {}

    with pytest.raises(RuntimeError, match="not running"):
        bridge.call_sync("dead-server", "tool", {})


@pytest.mark.asyncio
async def test_shutdown_all_closes_sessions(server_configs):
    """shutdown_all closes all active sessions."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    mock_session = MagicMock()
    mock_session.__aexit__ = AsyncMock()

    async def fake_close():
        pass

    mock_session.close = fake_close

    with patch.object(bridge, '_sessions', {"s1": mock_session}), \
         patch.object(bridge, '_processes', {"s1": MagicMock()}):
        bridge.shutdown_all()

    assert bridge._sessions == {}


def test_shutdown_all_force_kill(server_configs):
    """shutdown_all kills processes that don't exit gracefully within timeout."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.process = mock_proc

    with patch.object(bridge, '_sessions', {}), \
         patch.object(bridge, '_processes', {"s1": mock_proc}):
        bridge.shutdown_all()

    mock_proc.kill.assert_called_once()


def test_shutdown_all_noop_if_no_servers(server_configs):
    """shutdown_all with no sessions/processes is a no-op."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    bridge.shutdown_all()  # should not raise


@pytest.mark.asyncio
async def test_spawn_all_runs_on_bridge_loop(server_configs):
    """_spawn_one should create sessions on the bridge loop, not the caller's loop."""
    from aede.mcp.client import MCPBridge

    bridge = MCPBridge(servers=server_configs)
    main_loop = asyncio.get_running_loop()

    spawn_loop = None

    original_spawn = bridge._spawn_one
    async def tracking_spawn(name, cfg):
        nonlocal spawn_loop
        spawn_loop = asyncio.get_running_loop()

        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = "tracked_tool"
        mock_tool.description = ""
        mock_tool.inputSchema = {"type": "object"}
        mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

        with (
            patch("mcp.ClientSession", return_value=mock_session),
            patch("mcp.StdioServerParameters"),
            patch("mcp.client.stdio.stdio_client") as mock_stdio,
        ):
            mock_transport = MagicMock()
            mock_transport.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_transport.__aexit__ = AsyncMock()
            mock_stdio.return_value = mock_transport
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            return await original_spawn(name, cfg)

    bridge._spawn_one = tracking_spawn
    bridge.spawn_all()

    assert spawn_loop is not None, "_spawn_one was never called"
    assert spawn_loop is not main_loop, (
        f"_spawn_one ran on main loop ({id(main_loop)}) instead of bridge loop ({id(spawn_loop)})"
    )


@pytest.mark.asyncio
async def test_spawn_one_env_inherits_parent(server_configs):
    """_spawn_one merges cfg.env over os.environ, not replacing it entirely."""
    import os
    from aede.mcp.client import MCPBridge
    from unittest.mock import AsyncMock, MagicMock, patch

    bridge = MCPBridge(servers=server_configs)

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "t"
    mock_tool.description = ""
    mock_tool.inputSchema = {"type": "object"}
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

    captured_env = None

    with (
        patch("mcp.ClientSession", return_value=mock_session),
        patch("mcp.client.stdio.stdio_client") as mock_stdio,
    ):
        mock_transport = MagicMock()
        mock_transport.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
        mock_transport.__aexit__ = AsyncMock()
        mock_stdio.return_value = mock_transport
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

        # Monkey-patch StdioServerParameters to capture env
        real_params = __import__("mcp").StdioServerParameters
        def capturing_params(*args, **kwargs):
            nonlocal captured_env
            captured_env = kwargs.get("env") or (args[0].env if args else None)
            return real_params(*args, **kwargs) if args else MagicMock()

        with patch("mcp.StdioServerParameters", side_effect=capturing_params):
            # Set a test env var so we can verify inheritance
            os.environ["TEST_AEDE_MAGIC"] = "present"
            try:
                await bridge._spawn_one("test_server", server_configs["playwright"])
            finally:
                os.environ.pop("TEST_AEDE_MAGIC", None)

    assert captured_env is not None, "StdioServerParameters never created"
    assert captured_env.get("TEST_AEDE_MAGIC") == "present", (
        f"cfg.env should override but not replace parent env. Got env keys: {list(captured_env.keys())[:10]}..."
    )


@pytest.mark.asyncio
async def test_spawn_one_stores_process_handle(server_configs):
    """_spawn_one should extract and store the subprocess handle in _processes."""
    from aede.mcp.client import MCPBridge
    from unittest.mock import AsyncMock, MagicMock, patch

    bridge = MCPBridge(servers=server_configs)

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "t"
    mock_tool.description = ""
    mock_tool.inputSchema = {"type": "object"}
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

    with (
        patch("mcp.ClientSession", return_value=mock_session),
        patch("mcp.StdioServerParameters"),
        patch("mcp.client.stdio.stdio_client") as mock_stdio,
    ):
        mock_write = MagicMock()
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        # Simulate anyio stream transport with _proc
        mock_write._transport = MagicMock()
        mock_write._transport._proc = mock_proc

        mock_read = MagicMock()
        mock_transport = MagicMock()
        mock_transport.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_transport.__aexit__ = AsyncMock()
        mock_stdio.return_value = mock_transport
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        await bridge._spawn_one("test_server", server_configs["playwright"])

    assert "test_server" in bridge._processes, (
        "_processes should have entry after spawn"
    )
