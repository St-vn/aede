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
