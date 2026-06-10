from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Callable

import yaml

from aede.import_.claude_code import ImportReport


def import_mcp_servers_from_claude_code(
    src_config_path: Path,
    dest_config_path: Path,
    _input_fn: Callable[[str], str] | None = None,
) -> list[ImportReport]:
    """Import MCP server configs from a Claude Code mcp.json into aede config.yml.

    Reads ``mcpServers`` from the source JSON and appends each server
    to the ``mcp_servers`` section of the destination YAML config.
    Prompts before overwriting servers that already exist.
    """
    src_data: dict[str, Any] = json.loads(src_config_path.read_text(encoding="utf-8"))
    mcp_servers: dict[str, Any] = src_data.get("mcpServers", {})

    if not mcp_servers:
        return []

    dest_data: dict[str, Any] = {}
    if dest_config_path.exists():
        dest_data = yaml.safe_load(dest_config_path.read_text(encoding="utf-8")) or {}
    mcp_section = dest_data.get("mcp_servers") or {}
    dest_data["mcp_servers"] = mcp_section

    reports: list[ImportReport] = []

    for name, src_conf in mcp_servers.items():
        if not isinstance(src_conf, dict):
            continue

        server_conf: dict[str, Any] = {}

        raw_cmd = src_conf.get("command", "")
        if isinstance(raw_cmd, list):
            server_conf["command"] = raw_cmd[0] if raw_cmd else ""
            if len(raw_cmd) > 1:
                server_conf["args"] = raw_cmd[1:]
        else:
            server_conf["command"] = raw_cmd

        if "args" in src_conf:
            server_conf["args"] = src_conf["args"]

        if "env" in src_conf and src_conf["env"]:
            server_conf["env"] = src_conf["env"]

        if "trusted" in src_conf:
            server_conf["trusted"] = src_conf["trusted"]

        server_conf["enabled"] = True

        dest_path = dest_config_path
        report = ImportReport(name=name, dest_path=dest_path)

        if name in mcp_section:
            if _input_fn is None:
                raw = input(f"MCP server {name!r} already exists. Overwrite? [y/N] ")
            else:
                raw = _input_fn(f"MCP server {name!r} already exists. Overwrite? [y/N] ")
            if raw.lower() != "y":
                report.was_skipped = True
                reports.append(report)
                continue

        mcp_section[name] = server_conf
        reports.append(report)

    dest_config_path.write_text(
        yaml.dump(dest_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    return reports
