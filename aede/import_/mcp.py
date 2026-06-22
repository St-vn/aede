from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from aede.import_.claude_code import ImportReport


# Fields present in OpenAI Codex config that have no aede equivalent.
_CODEX_DROPPED_FIELDS = {
    "bearer_token_env_var",
    "startup_timeout_sec",
    "startup_timeout_ms",
    "tool_timeout_sec",
    "tool_timeout_ms",
    "cwd",
    "required",
    "enabled_tools",
    "scopes",
    "oauth_resource",
}


def import_mcp_from_json(
    src_config_path: Path,
    dest_config_path: Path,
    source: str = "MCP",
    _input_fn: Callable[[str], str] | None = None,
) -> list[ImportReport]:
    """Import MCP server configs from any JSON file that uses the shared
    ``mcpServers`` dict shape (Claude Code, Antigravity, Cursor, Windsurf).

    URL mapping:
    - ``serverUrl`` (Antigravity / Windsurf) → aede ``url``
    - ``url`` (Cursor) → aede ``url``

    Env values are passed through verbatim (no interpolation of ``${env:}``
    or ``${file:}`` tokens).

    Sets ``ImportReport.format`` to *source* on every report.
    Prompts before overwriting servers that already exist in dest.
    """
    import json
    import yaml

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

        # command — may be a list in some tools (e.g. Claude Code)
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

        # remote URL — accept both Antigravity/Windsurf "serverUrl" and Cursor "url"
        remote_url = src_conf.get("serverUrl") or src_conf.get("url")
        if remote_url:
            server_conf["url"] = remote_url

        server_conf["enabled"] = True

        if "disabled_tools" in src_conf:
            server_conf["disabled_tools"] = src_conf["disabled_tools"]

        report = ImportReport(name=name, dest_path=dest_config_path, format=source)

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


def import_mcp_servers_from_claude_code(
    src_config_path: Path,
    dest_config_path: Path,
    _input_fn: Callable[[str], str] | None = None,
) -> list[ImportReport]:
    """Import MCP server configs from a Claude Code mcp.json into aede config.yml.

    Delegates to :func:`import_mcp_from_json` with ``source="Claude Code"``.
    """
    return import_mcp_from_json(
        src_config_path=src_config_path,
        dest_config_path=dest_config_path,
        source="Claude Code",
        _input_fn=_input_fn,
    )


def import_mcp_from_toml(
    src_config_path: Path,
    dest_config_path: Path,
    source: str = "Codex",
    _input_fn: Callable[[str], str] | None = None,
) -> list[ImportReport]:
    """Import MCP server configs from an OpenAI Codex ``config.toml``.

    MCP servers live under the ``[mcp_servers]`` table.  Per-server field
    mapping to the aede shape:

    - ``command``        → 1:1
    - ``args``           → 1:1
    - ``env``            → 1:1 (only if non-empty)
    - ``url``            → 1:1 (only if present)
    - ``enabled``        → 1:1 (defaults to ``True`` when absent)
    - ``disabled_tools`` → 1:1 (only if present)

    The following Codex-specific fields are silently dropped:
    ``bearer_token_env_var``, ``startup_timeout_sec``, ``startup_timeout_ms``,
    ``tool_timeout_sec``, ``tool_timeout_ms``, ``cwd``, ``required``,
    ``enabled_tools``, ``scopes``, ``oauth_resource``.

    Sets ``ImportReport.format`` to *source* on every report.
    Prompts before overwriting servers that already exist in dest.
    """
    import tomllib
    import yaml

    # tomllib requires binary-mode open
    with src_config_path.open("rb") as fh:
        parsed: dict[str, Any] = tomllib.load(fh)

    mcp_servers: dict[str, Any] = parsed.get("mcp_servers", {})

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

        if "command" in src_conf:
            server_conf["command"] = src_conf["command"]

        if "args" in src_conf:
            server_conf["args"] = src_conf["args"]

        env = src_conf.get("env")
        if env:  # omit when absent or empty
            server_conf["env"] = dict(env)

        if "url" in src_conf:
            server_conf["url"] = src_conf["url"]

        # enabled: use source value if present, else default True
        server_conf["enabled"] = src_conf.get("enabled", True)

        if "disabled_tools" in src_conf:
            server_conf["disabled_tools"] = list(src_conf["disabled_tools"])

        # All _CODEX_DROPPED_FIELDS are intentionally not copied.

        report = ImportReport(name=name, dest_path=dest_config_path, format=source)

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
