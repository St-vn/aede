from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from aede.import_.claude_code import ImportReport


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


def _is_secret_var(name: str) -> bool:
    upper = name.upper()
    return (
        upper.endswith("_KEY")
        or upper.endswith("_TOKEN")
        or upper.endswith("_SECRET")
        or "PASSWORD" in upper
    )


def _validate_command(name: str, raw_cmd: Any) -> None:
    if not raw_cmd:
        raise ValueError(
            f"MCP server {name!r}: command is empty or missing in source config"
        )
    if isinstance(raw_cmd, list) and not all(isinstance(c, str) for c in raw_cmd):
        raise ValueError(
            f"MCP server {name!r}: command list elements must be strings"
        )


def _filter_secret_env(name: str, env: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    clean: dict[str, str] = {}
    skipped: list[str] = []
    for k, v in env.items():
        if _is_secret_var(k):
            skipped.append(k)
        else:
            clean[k] = v
    return clean, skipped


def import_mcp_from_json(
    src_config_path: Path,
    dest_config_path: Path,
    source: str = "MCP",
    _input_fn: Callable[[str], str] | None = None,
) -> list[ImportReport]:
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
        report = ImportReport(name=name, dest_path=dest_config_path, format=source)

        raw_cmd = src_conf.get("command", "")
        if "command" in src_conf:
            _validate_command(name, raw_cmd)
        if isinstance(raw_cmd, list):
            server_conf["command"] = raw_cmd[0] if raw_cmd else ""
            if len(raw_cmd) > 1:
                server_conf["args"] = raw_cmd[1:]
        else:
            server_conf["command"] = raw_cmd

        if "args" in src_conf:
            server_conf["args"] = src_conf["args"]

        if "env" in src_conf and src_conf["env"]:
            clean_env, skipped = _filter_secret_env(name, src_conf["env"])
            if clean_env:
                server_conf["env"] = clean_env
            for key in skipped:
                report.warnings.append(
                    f"Skipped secret env var {key!r} from MCP server {name!r}"
                )

        if "trusted" in src_conf:
            server_conf["trusted"] = src_conf["trusted"]

        remote_url = src_conf.get("serverUrl") or src_conf.get("url")
        if remote_url:
            server_conf["url"] = remote_url

        server_conf["enabled"] = True

        if "disabled_tools" in src_conf:
            server_conf["disabled_tools"] = src_conf["disabled_tools"]

        cmd_display = server_conf.get("command", "") or ""
        report.warnings.append(
            f"Imported MCP server {name!r} will execute command {cmd_display!r} on spawn \u2014 review before trusting"
        )

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
    import tomllib
    import yaml

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
        report = ImportReport(name=name, dest_path=dest_config_path, format=source)

        if "command" in src_conf:
            raw_cmd = src_conf["command"]
            _validate_command(name, raw_cmd)
            server_conf["command"] = raw_cmd

        if "args" in src_conf:
            server_conf["args"] = src_conf["args"]

        env = src_conf.get("env")
        if env:
            clean_env, skipped = _filter_secret_env(name, dict(env))
            if clean_env:
                server_conf["env"] = clean_env
            for key in skipped:
                report.warnings.append(
                    f"Skipped secret env var {key!r} from MCP server {name!r}"
                )

        if "url" in src_conf:
            server_conf["url"] = src_conf["url"]

        server_conf["enabled"] = src_conf.get("enabled", True)

        if "disabled_tools" in src_conf:
            server_conf["disabled_tools"] = list(src_conf["disabled_tools"])

        cmd_display = server_conf.get("command", "") or ""
        report.warnings.append(
            f"Imported MCP server {name!r} will execute command {cmd_display!r} on spawn \u2014 review before trusting"
        )

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
