import pytest
from pathlib import Path


def test_mcp_server_config_fields():
    """MCPServerConfig has command, args, env, trusted fields."""
    from aede.mcp.client import MCPServerConfig

    cfg = MCPServerConfig(
        command="npx",
        args=["-y", "@playwright/mcp"],
        env={"KEY": "val"},
        trusted=True,
    )
    assert cfg.command == "npx"
    assert cfg.args == ["-y", "@playwright/mcp"]
    assert cfg.env == {"KEY": "val"}
    assert cfg.trusted is True


def test_parse_mcp_servers_basic():
    """_parse_mcp_servers parses a YAML-like dict into MCPServerConfig dict."""
    from aede.mcp.client import _parse_mcp_servers, MCPServerConfig

    raw = {
        "playwright": {
            "command": "npx",
            "args": ["-y", "@playwright/mcp"],
            "env": {"KEY": "val"},
            "trusted": True,
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        },
    }

    result = _parse_mcp_servers(raw)
    assert "playwright" in result
    assert "filesystem" in result
    assert isinstance(result["playwright"], MCPServerConfig)
    assert result["playwright"].trusted is True
    assert result["filesystem"].trusted is False
    assert result["filesystem"].args == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]


def test_parse_mcp_servers_empty():
    """Empty dict returns empty dict."""
    from aede.mcp.client import _parse_mcp_servers

    assert _parse_mcp_servers({}) == {}


def test_parse_mcp_servers_none():
    """None returns empty dict."""
    from aede.mcp.client import _parse_mcp_servers

    assert _parse_mcp_servers(None) == {}


def test_mcp_server_config_enabled_defaults():
    """MCPServerConfig has enabled=True and disabled_tools=[] by default."""
    from aede.mcp.client import MCPServerConfig

    cfg = MCPServerConfig(command="echo")
    assert cfg.enabled is True
    assert cfg.disabled_tools == []


def test_mcp_server_config_explicit_disabled():
    """MCPServerConfig accepts explicit enabled/disabled_tools."""
    from aede.mcp.client import MCPServerConfig

    cfg = MCPServerConfig(command="echo", enabled=False, disabled_tools=["tool_a", "tool_b"])
    assert cfg.enabled is False
    assert cfg.disabled_tools == ["tool_a", "tool_b"]


def test_parse_mcp_servers_with_enabled_fields():
    """_parse_mcp_servers parses enabled and disabled_tools from raw dict."""
    from aede.mcp.client import _parse_mcp_servers

    raw = {
        "enabled_srv": {
            "command": "echo",
        },
        "disabled_srv": {
            "command": "echo",
            "enabled": False,
        },
        "filtered_srv": {
            "command": "echo",
            "disabled_tools": ["dangerous_tool"],
        },
    }

    result = _parse_mcp_servers(raw)
    assert result["enabled_srv"].enabled is True
    assert result["disabled_srv"].enabled is False
    assert result["filtered_srv"].disabled_tools == ["dangerous_tool"]
    assert result["enabled_srv"].disabled_tools == []
