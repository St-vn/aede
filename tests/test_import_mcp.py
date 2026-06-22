import json
import pytest
from pathlib import Path


def test_import_mcp_server_basic(tmp_path):
    """Basic import of a single MCP server from Claude Code mcp.json."""
    from aede.import_.mcp import import_mcp_servers_from_claude_code

    src = tmp_path / "mcp.json"
    src.write_text(json.dumps({
        "mcpServers": {
            "onshape": {
                "command": "C:/Users/megas/venv/Scripts/python.exe",
                "args": ["-m", "onshape_mcp.server"],
                "env": {
                    "ONSHAPE_ACCESS_KEY": "ak",
                    "ONSHAPE_SECRET_KEY": "sk",
                },
            }
        }
    }))

    dest = tmp_path / "config.yml"
    dest.write_text("mcp_servers:\n")

    reports = import_mcp_servers_from_claude_code(src_config_path=src, dest_config_path=dest)

    assert len(reports) == 1
    assert reports[0].name == "onshape"
    assert not reports[0].was_skipped

    import yaml
    data = yaml.safe_load(dest.read_text())
    srv = data["mcp_servers"]["onshape"]
    assert srv["command"] == "C:/Users/megas/venv/Scripts/python.exe"
    assert srv["args"] == ["-m", "onshape_mcp.server"]
    assert srv["env"]["ONSHAPE_ACCESS_KEY"] == "ak"
    assert srv["enabled"] is True


def test_import_mcp_merge_existing(tmp_path):
    """Import when server already exists prompts and preserves original if declined."""
    from aede.import_.mcp import import_mcp_servers_from_claude_code

    src = tmp_path / "mcp.json"
    src.write_text(json.dumps({
        "mcpServers": {
            "robloxstudio": {
                "command": "npx",
                "args": ["-y", "robloxstudio-mcp@latest"],
            }
        }
    }))

    dest = tmp_path / "config.yml"
    dest.write_text("mcp_servers:\n  robloxstudio:\n    command: old-cmd\n    args: []\n    enabled: true\n")

    reports = import_mcp_servers_from_claude_code(
        src_config_path=src, dest_config_path=dest, _input_fn=lambda p: "n",
    )

    assert len(reports) == 1
    assert reports[0].was_skipped

    import yaml
    data = yaml.safe_load(dest.read_text())
    srv = data["mcp_servers"]["robloxstudio"]
    assert srv["command"] == "old-cmd"


def test_import_mcp_multiple_servers(tmp_path):
    """Import with 2+ servers — all appear in dest."""
    from aede.import_.mcp import import_mcp_servers_from_claude_code

    src = tmp_path / "mcp.json"
    src.write_text(json.dumps({
        "mcpServers": {
            "server-a": {"command": "cmd-a", "args": ["a1"]},
            "server-b": {"command": "cmd-b", "args": ["b1"], "env": {"X": "1"}},
        }
    }))

    dest = tmp_path / "config.yml"
    dest.write_text("mcp_servers:\n")

    reports = import_mcp_servers_from_claude_code(src_config_path=src, dest_config_path=dest)

    assert len(reports) == 2
    names = {r.name for r in reports}
    assert names == {"server-a", "server-b"}

    import yaml
    data = yaml.safe_load(dest.read_text())
    assert "server-a" in data["mcp_servers"]
    assert "server-b" in data["mcp_servers"]
    assert data["mcp_servers"]["server-b"]["env"] == {"X": "1"}


def test_import_mcp_no_mcp_servers_key(tmp_path):
    """Import when mcp.json has no mcpServers key returns empty list."""
    from aede.import_.mcp import import_mcp_servers_from_claude_code

    src = tmp_path / "mcp.json"
    src.write_text(json.dumps({"other": "data"}))

    dest = tmp_path / "config.yml"
    dest.write_text("mcp_servers:\n")

    reports = import_mcp_servers_from_claude_code(src_config_path=src, dest_config_path=dest)

    assert reports == []
