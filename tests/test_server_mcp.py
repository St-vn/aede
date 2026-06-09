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


def test_create_mcp_server_with_enabled_fields(tmp_path, monkeypatch):
    """POST /api/mcp/servers persists enabled and disabled_tools."""
    from aede.config import load_config

    cfg = load_config()
    monkeypatch.setattr(cfg, "home", tmp_path)
    app.state.cfg = cfg
    app.state.mcp_bridge = None

    config_file = tmp_path / "config.yml"
    config_file.write_text("mcp_servers: {}\n", encoding="utf-8")

    client = TestClient(app)
    resp = client.post("/api/mcp/servers", json={
        "name": "new_srv", "command": "echo", "args": ["hello"],
        "enabled": False, "disabled_tools": ["danger"],
    })
    assert resp.status_code == 200

    import yaml
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    entry = data["mcp_servers"]["new_srv"]
    assert entry["enabled"] is False
    assert entry["disabled_tools"] == ["danger"]


def test_update_mcp_server_toggles_enabled(tmp_path, monkeypatch):
    """PUT /api/mcp/servers/{name} updates fields without affecting others."""
    from aede.config import load_config

    cfg = load_config()
    monkeypatch.setattr(cfg, "home", tmp_path)
    app.state.cfg = cfg
    app.state.mcp_bridge = None

    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "mcp_servers:\n  my_server:\n    command: echo\n    enabled: true\n    disabled_tools: []\n",
        encoding="utf-8",
    )

    client = TestClient(app)
    # Disable it
    resp = client.put("/api/mcp/servers/my_server", json={"enabled": False})
    assert resp.status_code == 200

    import yaml
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    entry = data["mcp_servers"]["my_server"]
    assert entry["enabled"] is False
    assert entry["command"] == "echo"  # other fields preserved


def test_update_mcp_server_disabled_tools(tmp_path, monkeypatch):
    """PUT /api/mcp/servers/{name} updates disabled_tools."""
    from aede.config import load_config

    cfg = load_config()
    monkeypatch.setattr(cfg, "home", tmp_path)
    app.state.cfg = cfg
    app.state.mcp_bridge = None

    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "mcp_servers:\n  my_server:\n    command: echo\n    enabled: true\n    disabled_tools: []\n",
        encoding="utf-8",
    )

    client = TestClient(app)
    resp = client.put("/api/mcp/servers/my_server", json={"disabled_tools": ["tool_a", "tool_b"]})
    assert resp.status_code == 200

    import yaml
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert data["mcp_servers"]["my_server"]["disabled_tools"] == ["tool_a", "tool_b"]


def test_update_mcp_server_not_found(tmp_path, monkeypatch):
    """PUT /api/mcp/servers/{name} returns 404 for unknown server."""
    from aede.config import load_config

    cfg = load_config()
    monkeypatch.setattr(cfg, "home", tmp_path)
    app.state.cfg = cfg
    app.state.mcp_bridge = None

    config_file = tmp_path / "config.yml"
    config_file.write_text("mcp_servers: {}\n", encoding="utf-8")

    client = TestClient(app)
    resp = client.put("/api/mcp/servers/nonexistent", json={"enabled": False})
    assert resp.status_code == 404


def test_delete_mcp_server_removes_entry(tmp_path, monkeypatch):
    """DELETE /api/mcp/servers/{name} removes the server from config.yml."""
    from aede.config import load_config

    cfg = load_config()
    monkeypatch.setattr(cfg, "home", tmp_path)
    app.state.cfg = cfg
    app.state.mcp_bridge = None

    config_file = tmp_path / "config.yml"
    config_file.write_text(
        "mcp_servers:\n  to_delete:\n    command: echo\n    enabled: true\n",
        encoding="utf-8",
    )

    client = TestClient(app)
    resp = client.delete("/api/mcp/servers/to_delete")
    assert resp.status_code == 200

    import yaml
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert "to_delete" not in data["mcp_servers"]


def test_create_mcp_server_preserves_enabled_default(tmp_path, monkeypatch):
    """POST /api/mcp/servers defaults enabled to True when not provided."""
    from aede.config import load_config

    cfg = load_config()
    monkeypatch.setattr(cfg, "home", tmp_path)
    app.state.cfg = cfg
    app.state.mcp_bridge = None

    config_file = tmp_path / "config.yml"
    config_file.write_text("mcp_servers: {}\n", encoding="utf-8")

    client = TestClient(app)
    resp = client.post("/api/mcp/servers", json={
        "name": "simple", "command": "echo",
    })
    assert resp.status_code == 200

    import yaml
    data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert data["mcp_servers"]["simple"]["enabled"] is True
