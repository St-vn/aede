"""Tests for MCP server endpoints."""
import pytest
from fastapi.testclient import TestClient
from aede.server import app
from aede.mcp.client import MCPServerConfig


@pytest.fixture
def client_with_mcp_config():
    """Set up app state with an MCP server config and test bridge."""
    from aede.config import load_config
    from unittest.mock import MagicMock

    cfg = load_config()
    cfg.mcp_servers = {
        "test_srv": MCPServerConfig(
            command="echo",
            args=["hello"],
            env={},
            trusted=False,
            enabled=True,
            disabled_tools=["tool_b"],
        ),
    }
    app.state.cfg = cfg

    mock_bridge = MagicMock()
    mock_bridge._tool_schemas = {
        "test_srv": [
            {"name": "tool_a", "description": "Tool A", "input_schema": {"type": "object"}},
            {"name": "tool_b", "description": "Tool B", "input_schema": {"type": "object"}},
        ],
    }
    mock_bridge._sessions = {"test_srv": MagicMock()}
    app.state.mcp_bridge = mock_bridge

    yield TestClient(app)

    app.state.mcp_bridge = None


def test_get_mcp_servers_includes_new_fields(client_with_mcp_config):
    """GET /api/mcp/servers returns enabled, disabled_tools, and tools per server."""
    resp = client_with_mcp_config.get("/api/mcp/servers")
    assert resp.status_code == 200
    data = resp.json()

    assert "test_srv" in data
    info = data["test_srv"]

    assert info["enabled"] is True
    assert info["disabled_tools"] == ["tool_b"]
    assert "tools" in info
    assert isinstance(info["tools"], list)

    tool_names = [t["name"] for t in info["tools"]]
    assert "tool_a" in tool_names
    assert "tool_b" in tool_names


def test_get_mcp_servers_empty_tools_when_no_bridge():
    """When bridge is None, tools is empty list."""
    from aede.config import load_config

    cfg = load_config()
    cfg.mcp_servers = {
        "offline_srv": MCPServerConfig(command="echo"),
    }
    app.state.cfg = cfg
    app.state.mcp_bridge = None

    client = TestClient(app)
    resp = client.get("/api/mcp/servers")
    data = resp.json()

    assert data["offline_srv"]["tools"] == []
