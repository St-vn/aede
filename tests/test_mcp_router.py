import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_mcp_tools():
    """Return a list of discovered MCP tools from a bridge."""
    return [
        ("mcp__playwright__navigate", "playwright",
         MagicMock(command="npx", args=[], env={}, trusted=False),
         {"name": "mcp__playwright__navigate", "description": "Go to URL",
          "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}}}),
        ("mcp__playwright__click", "playwright",
         MagicMock(command="npx", args=[], env={}, trusted=False),
         {"name": "mcp__playwright__click", "description": "Click element",
          "input_schema": {"type": "object", "properties": {"selector": {"type": "string"}}}}),
    ]


def test_register_mcp_tools_adds_to_registry(sample_mcp_tools):
    """register_mcp_tools inserts mcp__* tools into router._registry."""
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router.register_mcp_tools(sample_mcp_tools)

    names = router.tool_names()
    assert "mcp__playwright__navigate" in names
    assert "mcp__playwright__click" in names


def test_anthropic_tool_schemas_includes_mcp_tools(sample_mcp_tools):
    """anthropic_tool_schemas includes MCP tool schemas."""
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router.register_mcp_tools(sample_mcp_tools)

    schemas = router.anthropic_tool_schemas()
    names = [s["name"] for s in schemas]
    assert "mcp__playwright__navigate" in names


def test_requires_approval_untrusted_mcp_tool(sample_mcp_tools):
    """Untrusted MCP tool requires approval."""
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router.register_mcp_tools(sample_mcp_tools)

    assert router.requires_approval("mcp__playwright__navigate") is True


def test_requires_approval_trusted_mcp_tool():
    """Trusted MCP tool does NOT require approval."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock

    trusted_tools = [
        ("mcp__playwright__navigate", "playwright",
         MagicMock(command="npx", args=[], env={}, trusted=True),
         {"name": "mcp__playwright__navigate", "description": "Go to URL",
          "input_schema": {"type": "object"}}),
    ]

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router.register_mcp_tools(trusted_tools)

    assert router.requires_approval("mcp__playwright__navigate") is False


def test_requires_approval_session_allow(sample_mcp_tools):
    """Session-level allow overrides untrusted status."""
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router.register_mcp_tools(sample_mcp_tools)
    router.set_auto_approved(["mcp__playwright__navigate"])

    assert router.requires_approval("mcp__playwright__navigate") is False


def test_execute_sync_mcp_tool_delegation(sample_mcp_tools):
    """execute_sync with mcp__ prefix delegates to bridge.call_sync."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock

    bridge = MagicMock()
    bridge.call_sync.return_value = "done"

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router._mcp_bridge = bridge
    router.register_mcp_tools(sample_mcp_tools)

    result = router.execute_sync("mcp__playwright__navigate", {"url": "https://example.com"})

    bridge.call_sync.assert_called_once_with("playwright", "navigate", {"url": "https://example.com"})
    assert result.output == "done"


def test_execute_sync_mcp_delegation_and_builtin_unchanged(sample_mcp_tools):
    """Built-in tools still execute normally despite MCP tools being registered."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock

    bridge = MagicMock()
    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router._mcp_bridge = bridge
    router.register_mcp_tools(sample_mcp_tools)

    result = router.execute_sync("read_file", {"path": "test.txt"})
    assert result.status == "error"  # file doesn't exist
    bridge.call_sync.assert_not_called()


def test_execute_sync_mcp_lazy_bridge_resolves_each_call(sample_mcp_tools):
    """MCP handler calls _get_bridge on each invocation (not cached at registration)."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock

    bridge_a = MagicMock()
    bridge_a.call_sync.return_value = "from bridge A"

    call_count = 0

    def get_bridge():
        nonlocal call_count
        call_count += 1
        return bridge_a

    router = ToolRouter(
        shell="powershell", wsl_distro="", tool_output_max_tokens=8000,
        _get_bridge=get_bridge,
    )
    router.register_mcp_tools(sample_mcp_tools)

    result = router.execute_sync("mcp__playwright__navigate", {"url": "x"})
    assert result.output == "from bridge A"
    assert call_count == 1

    result2 = router.execute_sync("mcp__playwright__click", {"selector": ".btn"})
    assert result2.output == "from bridge A"
    assert call_count == 2  # called again, not cached


def test_execute_sync_mcp_lazy_bridge_replaced(sample_mcp_tools):
    """When _get_bridge returns a new bridge, MCP handler uses the new one."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock

    current_bridge = MagicMock()
    current_bridge.call_sync.return_value = "from bridge A"

    def get_bridge():
        return current_bridge

    router = ToolRouter(
        shell="powershell", wsl_distro="", tool_output_max_tokens=8000,
        _get_bridge=get_bridge,
    )
    router.register_mcp_tools(sample_mcp_tools)

    r1 = router.execute_sync("mcp__playwright__navigate", {"url": "x"})
    assert r1.output == "from bridge A"

    # Simulate a bridge restart — swap the underlying bridge
    new_bridge = MagicMock()
    new_bridge.call_sync.return_value = "from brand new bridge"
    current_bridge = new_bridge

    r2 = router.execute_sync("mcp__playwright__navigate", {"url": "y"})
    assert r2.output == "from brand new bridge"


def test_execute_sync_mcp_lazy_bridge_becomes_none(sample_mcp_tools):
    """When _get_bridge returns None, handler returns the error string."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock

    bridge = MagicMock()
    bridge.call_sync.return_value = "ok"

    bridge_ref = [bridge]  # boxed so we can clear it

    def get_bridge():
        return bridge_ref[0]

    router = ToolRouter(
        shell="powershell", wsl_distro="", tool_output_max_tokens=8000,
        _get_bridge=get_bridge,
    )
    router.register_mcp_tools(sample_mcp_tools)

    r1 = router.execute_sync("mcp__playwright__navigate", {"url": "x"})
    assert r1.output == "ok"

    bridge_ref[0] = None  # bridge goes away

    r2 = router.execute_sync("mcp__playwright__navigate", {"url": "y"})
    assert "[error: MCP bridge not initialized]" in r2.output


def test_execute_sync_mcp_stored_bridge_still_works(sample_mcp_tools):
    """Backward compat: setting _mcp_bridge directly still works when no _get_bridge set."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock

    bridge = MagicMock()
    bridge.call_sync.return_value = "stored bridge works"

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router._mcp_bridge = bridge
    router.register_mcp_tools(sample_mcp_tools)

    result = router.execute_sync("mcp__playwright__navigate", {"url": "x"})
    assert result.output == "stored bridge works"
