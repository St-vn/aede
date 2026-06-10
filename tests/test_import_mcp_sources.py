"""Tests for import_mcp_from_json and import_mcp_from_toml."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _load_dest(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ---------------------------------------------------------------------------
# import_mcp_from_json
# ---------------------------------------------------------------------------

class TestImportMcpFromJson:
    def test_antigravity_server_url_mapped_to_url(self, tmp_path):
        """Antigravity-style serverUrl is mapped to aede `url`."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "ag.json", {
            "mcpServers": {
                "ag-search": {
                    "serverUrl": "https://mcp.antigravity.dev/search",
                    "env": {"AG_KEY": "secret"},
                }
            }
        })
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_json(src, dest, source="Antigravity")

        assert len(reports) == 1
        assert reports[0].name == "ag-search"
        assert not reports[0].was_skipped
        assert reports[0].format == "Antigravity"

        srv = _load_dest(dest)["mcp_servers"]["ag-search"]
        assert srv["url"] == "https://mcp.antigravity.dev/search"
        assert srv["env"]["AG_KEY"] == "secret"
        assert srv["enabled"] is True
        # command should not be present for a remote-only entry (no command key)
        assert srv.get("command", "") == ""

    def test_cursor_url_field_mapped_to_url(self, tmp_path):
        """Cursor-style `url` field is mapped to aede `url`."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "cursor.json", {
            "mcpServers": {
                "cursor-remote": {
                    "url": "https://mcp.cursor.sh/remote",
                }
            }
        })
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_json(src, dest, source="Cursor")

        assert len(reports) == 1
        srv = _load_dest(dest)["mcp_servers"]["cursor-remote"]
        assert srv["url"] == "https://mcp.cursor.sh/remote"
        assert reports[0].format == "Cursor"

    def test_windsurf_env_interpolation_preserved_verbatim(self, tmp_path):
        """Windsurf ${env:VAR} / ${file:} strings are kept as-is."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "ws.json", {
            "mcpServers": {
                "ws-server": {
                    "command": "npx",
                    "args": ["-y", "ws-mcp"],
                    "env": {
                        "TOKEN": "${env:MY_TOKEN}",
                        "CERT": "${file:/home/user/.cert}",
                    },
                }
            }
        })
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_json(src, dest, source="Windsurf")

        srv = _load_dest(dest)["mcp_servers"]["ws-server"]
        assert srv["env"]["TOKEN"] == "${env:MY_TOKEN}"
        assert srv["env"]["CERT"] == "${file:/home/user/.cert}"
        assert reports[0].format == "Windsurf"

    def test_format_tag_set_on_each_report(self, tmp_path):
        """format attribute on each report matches the `source` argument."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "src.json", {
            "mcpServers": {
                "s1": {"command": "cmd1"},
                "s2": {"command": "cmd2"},
            }
        })
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_json(src, dest, source="MyTool")

        assert all(r.format == "MyTool" for r in reports)

    def test_stdio_server_works_without_url(self, tmp_path):
        """A plain stdio server (command + args) imports correctly."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "src.json", {
            "mcpServers": {
                "stdio-srv": {
                    "command": "python",
                    "args": ["-m", "myserver"],
                    "env": {"X": "1"},
                    "trusted": True,
                }
            }
        })
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_json(src, dest)

        srv = _load_dest(dest)["mcp_servers"]["stdio-srv"]
        assert srv["command"] == "python"
        assert srv["args"] == ["-m", "myserver"]
        assert srv["env"] == {"X": "1"}
        assert srv["trusted"] is True
        assert srv["enabled"] is True
        # url should NOT appear for a pure stdio server
        assert "url" not in srv

    def test_overwrite_declined_skips_and_preserves_original(self, tmp_path):
        """When user declines overwrite, was_skipped=True and original unchanged."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "src.json", {
            "mcpServers": {
                "existing": {
                    "command": "new-cmd",
                    "args": ["new-arg"],
                }
            }
        })
        dest = tmp_path / "config.yml"
        dest.write_text(
            "mcp_servers:\n  existing:\n    command: old-cmd\n    args: []\n    enabled: true\n"
        )

        reports = import_mcp_from_json(src, dest, _input_fn=lambda _: "n")

        assert len(reports) == 1
        assert reports[0].was_skipped is True

        srv = _load_dest(dest)["mcp_servers"]["existing"]
        assert srv["command"] == "old-cmd"

    def test_command_as_list_splits_into_command_and_args(self, tmp_path):
        """When command is a list, first element → command, rest → args."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "src.json", {
            "mcpServers": {
                "list-cmd": {
                    "command": ["/usr/bin/python3", "-m", "server"],
                }
            }
        })
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_json(src, dest)

        srv = _load_dest(dest)["mcp_servers"]["list-cmd"]
        assert srv["command"] == "/usr/bin/python3"
        assert srv["args"] == ["-m", "server"]

    def test_default_source_label_is_mcp(self, tmp_path):
        """Default source label when no `source` arg passed is 'MCP'."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "src.json", {
            "mcpServers": {"s": {"command": "c"}}
        })
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_json(src, dest)

        assert reports[0].format == "MCP"

    def test_empty_mcpservers_returns_empty_list(self, tmp_path):
        """If mcpServers is absent or empty, returns []."""
        from aede.import_.mcp import import_mcp_from_json

        src = _write_json(tmp_path / "src.json", {"mcpServers": {}})
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_json(src, dest)

        assert reports == []


# ---------------------------------------------------------------------------
# import_mcp_from_toml
# ---------------------------------------------------------------------------

class TestImportMcpFromToml:
    def _write_toml(self, path: Path, text: str) -> Path:
        path.write_text(textwrap.dedent(text), encoding="utf-8")
        return path

    def test_basic_command_and_args(self, tmp_path):
        """Simple [mcp_servers.db] table with command + args."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.db]
            command = "sqlite-mcp"
            args = ["--db", "/data/app.db"]
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_toml(toml_path, dest)

        assert len(reports) == 1
        assert reports[0].name == "db"
        assert reports[0].format == "Codex"

        srv = _load_dest(dest)["mcp_servers"]["db"]
        assert srv["command"] == "sqlite-mcp"
        assert srv["args"] == ["--db", "/data/app.db"]
        assert srv["enabled"] is True

    def test_env_as_toml_table(self, tmp_path):
        """[mcp_servers.db.env] table is mapped to env dict."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.db]
            command = "sqlite-mcp"
            args = []

            [mcp_servers.db.env]
            DB_USER = "admin"
            DB_PASS = "secret"
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["db"]
        assert srv["env"] == {"DB_USER": "admin", "DB_PASS": "secret"}

    def test_env_as_inline_table(self, tmp_path):
        """Inline TOML env = {A = "1"} is also mapped correctly."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.inline]
            command = "my-srv"
            args = []
            env = {A = "1", B = "2"}
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["inline"]
        assert srv["env"] == {"A": "1", "B": "2"}

    def test_remote_server_url_mapped(self, tmp_path):
        """url field is mapped 1:1; bearer_token_env_var is dropped."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.docs]
            url = "https://mcp.example.com/docs"
            bearer_token_env_var = "DOCS_TOKEN"
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["docs"]
        assert srv["url"] == "https://mcp.example.com/docs"
        assert "bearer_token_env_var" not in srv

    def test_all_dropped_fields_absent_from_dest(self, tmp_path):
        """All Codex-specific fields are dropped silently."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.full]
            command = "srv"
            args = []
            bearer_token_env_var = "T"
            startup_timeout_sec = 30
            startup_timeout_ms = 30000
            tool_timeout_sec = 10
            tool_timeout_ms = 10000
            cwd = "/tmp"
            required = true
            scopes = ["read", "write"]
            oauth_resource = "https://example.com"
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["full"]
        dropped = {
            "bearer_token_env_var", "startup_timeout_sec", "startup_timeout_ms",
            "tool_timeout_sec", "tool_timeout_ms", "cwd", "required",
            "enabled_tools", "scopes", "oauth_resource",
        }
        for field in dropped:
            assert field not in srv, f"dropped field {field!r} leaked into dest"

    def test_enabled_field_preserved(self, tmp_path):
        """If enabled is explicitly set in TOML, it is respected."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.off]
            command = "srv"
            args = []
            enabled = false
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["off"]
        assert srv["enabled"] is False

    def test_enabled_defaults_to_true_when_absent(self, tmp_path):
        """enabled defaults to True when not in source."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.svc]
            command = "svc"
            args = []
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["svc"]
        assert srv["enabled"] is True

    def test_disabled_tools_mapped(self, tmp_path):
        """disabled_tools list is mapped 1:1."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.limited]
            command = "srv"
            args = []
            disabled_tools = ["tool_x", "tool_y"]
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["limited"]
        assert srv["disabled_tools"] == ["tool_x", "tool_y"]

    def test_multiple_servers(self, tmp_path):
        """Multiple [mcp_servers.*] sections are all imported."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.alpha]
            command = "alpha"
            args = []

            [mcp_servers.beta]
            command = "beta"
            args = ["--flag"]

            [mcp_servers.gamma]
            url = "https://gamma.example.com"
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_toml(toml_path, dest)

        assert len(reports) == 3
        names = {r.name for r in reports}
        assert names == {"alpha", "beta", "gamma"}

        data = _load_dest(dest)["mcp_servers"]
        assert data["beta"]["args"] == ["--flag"]
        assert data["gamma"]["url"] == "https://gamma.example.com"

    def test_overwrite_declined_preserves_original(self, tmp_path):
        """Declining overwrite on an existing server keeps original."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.existing]
            command = "new-cmd"
            args = []
        """)
        dest = tmp_path / "config.yml"
        dest.write_text(
            "mcp_servers:\n  existing:\n    command: old-cmd\n    args: []\n    enabled: true\n"
        )

        reports = import_mcp_from_toml(toml_path, dest, _input_fn=lambda _: "n")

        assert reports[0].was_skipped is True
        assert _load_dest(dest)["mcp_servers"]["existing"]["command"] == "old-cmd"

    def test_no_mcp_servers_section_returns_empty(self, tmp_path):
        """A TOML with no [mcp_servers] table returns []."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [settings]
            theme = "dark"
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_toml(toml_path, dest)

        assert reports == []

    def test_format_is_codex_by_default(self, tmp_path):
        """Default format label is 'Codex'."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.x]
            command = "x"
            args = []
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        reports = import_mcp_from_toml(toml_path, dest)

        assert reports[0].format == "Codex"

    def test_empty_env_not_written_to_dest(self, tmp_path):
        """env key is absent from dest when source env is empty."""
        from aede.import_.mcp import import_mcp_from_toml

        toml_path = self._write_toml(tmp_path / "config.toml", """\
            [mcp_servers.svc]
            command = "svc"
            args = []
            env = {}
        """)
        dest = tmp_path / "config.yml"
        dest.write_text("mcp_servers:\n")

        import_mcp_from_toml(toml_path, dest)

        srv = _load_dest(dest)["mcp_servers"]["svc"]
        assert "env" not in srv
