"""
Slash-command parsing and handler functions for the aede REPL.

Recognises ``/command [args...]`` lines typed at the prompt, parses them into
``CommandResult`` values, and implements each handler (help, sessions, tools,
tokens, config, setkey).  The CLI loop in ``cli.py`` calls these handlers
directly.
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


COMMANDS = {
    "help", "keybinds", "resume", "sessions", "tools", "config",
    "compact", "tokens", "clear", "exit", "setkey",
    "skills", "agents", "mcp", "delete-session", "rm", "acp", "import",
    "extract", "soul", "rename", "approve",
}


@dataclass
class CommandResult:
    """Parsed representation of a slash-command entered by the user."""

    name: str
    args: list[str] = field(default_factory=list)


def parse_command(text: str) -> CommandResult | None:
    """Parse a REPL input line as a slash-command.

    Returns ``None`` if the line does not start with ``/`` or names an
    unrecognised command, so the caller can fall through to the agent.
    """
    text = text.strip()
    if not text.startswith("/"):
        return None
    parts = text[1:].split()
    if not parts:
        return None
    name = parts[0].lower()
    if name not in COMMANDS:
        return None
    return CommandResult(name=name, args=parts[1:])


def handle_help(console: Any) -> None:
    """Print the list of available slash-commands."""
    console.print(
        "\n".join([
            "Available commands:",
            "  /help                         — this list",
            "  /keybinds                     — show keyboard shortcuts",
            "  /resume [id]                  — resume a session",
            "  /sessions                     — list recent sessions",
            "  /delete-session [id]          — delete a session (alias: /rm)",
            "  /tools                        — list tools and approval status",
            "  /skills                       — list loaded skills",
            "  /agents                       — list loaded agents",
            "  /mcp                          — list MCP servers and tools",
            "  /config [scope] [key] [value] — view or set config",
            "  /compact                      — manually compact context",
            "  /tokens                       — show token usage and cost",
            "  /setkey <NAME> <value>        — save a credential to aede's vault (loaded on every launch)",
            "  /soul [view|global|project|<key> <value>] — view or edit soul definition",
            "  /import agent <path> [--source] — import an agent/rules file (claude-code, opencode, antigravity, codex, cursor, windsurf)",
            "  /import skill <path> [--source] — import a SKILL.md (claude-code, antigravity, codex, windsurf)",
            "  /import mcp <path> [--source]   — import MCP servers (JSON or Codex TOML)",
            "  /import all [--source <name>]   — import everything from a source's standard dirs",
            "  /acp register <name> <cmd...>  — register an ACP agent",
            "  /acp connect <name>            — connect to an ACP agent (use its subscription as backend)",
            "  /acp disconnect                — disconnect from the ACP agent, return to normal mode",
            "  /acp list                      — show connected ACP agents",
            "  /acp configs                   — show registered ACP agent configs",
            "  /extract [id]                 — extract learnings from a session trace",
            "  /clear                        — start a new session",
            "  /exit                         — end session cleanly",
        ])
    )


def handle_keybinds(console: Any) -> None:
    """Print the keyboard shortcuts active in the REPL loop."""
    console.print(
        "\n".join([
            "Keyboard shortcuts:",
            "  Enter                         — submit the current line",
            "  Ctrl+C                        — end session, stays resumable (active)",
            "  Ctrl+D                        — end session cleanly (archived)",
        ])
    )


def handle_sessions(db: Any, console: Any) -> None:
    """Print the 20 most recent sessions with humanised age and truncated title."""
    from aede.session import Session
    sessions = Session.list_recent(db=db, limit=20)
    if not sessions:
        console.print("No sessions yet.")
        return
    import time
    now = time.time() * 1000
    for i, s in enumerate(sessions, 1):
        age_ms = now - s.updated_at
        age_str = _humanize_age(age_ms)
        indent = "  " if s.parent_id else ""
        prefix = "└" if s.parent_id else str(i)
        title = s.title or "(untitled)"
        console.print(f"  {prefix}  {age_str:12}  {indent}{title[:60]}")


def handle_rename(args: list[str], session: Any, db: Any, console: Any) -> None:
    """Rename the current session.

    Usage:
      /rename <new title>
    """
    if not args:
        console.print("[yellow]Usage: /rename <new title>[/yellow]")
        return
    title = " ".join(args)
    session.set_title(db, title)
    console.print(f"[green]✓[/green] Session renamed to \"{title}\"")


def handle_approve(args: list[str], router: Any, gate_store: Any, console: Any) -> None:
    """Batch-approve gated tools for the current session.

    Usage:
      /approve                      — show gated tools
      /approve <tool> [tool...]     — approve specific tools
    """
    if args:
        router.set_auto_approved(args)
        console.print(f"[green]✓[/green] Approved: {', '.join(args)}")
        return

    from aede.tools.router import GATE_TOOLS
    lines = ["Gated tools:"]
    for name in sorted(router.tool_names()):
        if name in GATE_TOOLS or name.startswith("mcp__"):
            status = "approved" if name in router._session_auto_approve else "gated"
            lines.append(f"  {name:<25} [{status}]")
    console.print("\n".join(lines))


def handle_tools(router: Any, console: Any) -> None:
    """Print all registered tools with their approval mode (gate vs auto)."""
    from aede.tools.router import GATE_TOOLS
    lines = ["Available tools:"]
    for name in router.tool_names():
        approval = "gate" if name in GATE_TOOLS else "auto"
        allowed = " [always allowed]" if router._session_auto_approve and name in router._session_auto_approve else ""
        lines.append(f"  {name:<20} {approval}{allowed}")
    console.print("\n".join(lines))


def handle_skills(skill_registry: dict[str, Any], console: Any) -> None:
    """Print all loaded skills as a table with Name, Description (60-char), and Source."""
    if not skill_registry:
        console.print("No skills loaded.")
        return
    lines = ["Skills:"]
    for name, skill in sorted(skill_registry.items()):
        desc = (skill.description[:60] + "...") if len(skill.description) > 60 else skill.description
        lines.append(f"  {name:<25} {desc}")
    console.print("\n".join(lines))


def handle_agents(agent_registry: dict[str, Any], console: Any) -> None:
    """Print all loaded agents as a table with Name, Description, Model."""
    if not agent_registry:
        console.print("No agents loaded.")
        return
    lines = ["Agents:"]
    for name, agent in sorted(agent_registry.items()):
        desc = (agent.description[:60] + "...") if len(agent.description) > 60 else agent.description
        model_str = agent.model if agent.model != "inherit" else "inherit"
        lines.append(f"  {name:<25} {desc:<62} {model_str}")
    console.print("\n".join(lines))


def handle_mcp(mcp_servers: dict[str, Any], console: Any) -> None:
    """Print all configured MCP servers with status and tool count."""
    if not mcp_servers:
        console.print("No MCP servers configured.")
        return
    lines = ["MCP Servers:"]
    for name, srv in sorted(mcp_servers.items()):
        status = "enabled" if srv.enabled else "disabled"
        cmd = srv.command or ""
        args_str = " ".join(srv.args[:2]) if srv.args else ""
        tool_hint = f" ({len(srv.disabled_tools)} disabled)" if srv.disabled_tools else ""
        lines.append(f"  {name:<25} [{status}] {cmd} {args_str}{tool_hint}")
    console.print("\n".join(lines))


async def handle_acp(args: list[str], acp_manager: Any, console: Any) -> str | None:
    """Handle ACP agent lifecycle commands.

    Subcommands:
      register <name> <command> [args...]  — register an ACP agent config.
      connect <name>                       — connect to an ACP agent.
      disconnect                           — disconnect from the active ACP agent.
      list                                 — show connected ACP agents.
      configs                              — show registered ACP agent configs.

    Returns:
      ``"connected"`` if a connect was just performed (so the caller can
      enter ACP routing mode), or ``None`` otherwise.
    """
    if not args:
        console.print("Usage: /acp {register|connect|disconnect|list|configs}")
        return None

    sub = args[0].lower()

    if sub == "register":
        if len(args) < 3:
            console.print("Usage: /acp register <name> <command> [args...]")
            return None
        name = args[1]
        command = args[2]
        extra_args = args[3:]
        from aede.acp.registry import AgentConfig, AgentTransport
        config = AgentConfig(
            name=name,
            transport=AgentTransport.LOCAL,
            command=command,
            args=extra_args,
        )
        try:
            acp_manager._registry.add(config)
            console.print(f"[green]✓[/green] Registered ACP agent '{name}' → {command}")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
        return None

    if sub == "connect":
        if len(args) < 2:
            console.print("Usage: /acp connect <name>")
            console.print("Registered configs:")
            for c in acp_manager._registry.list_all():
                console.print(f"  {c.name:<20} {c.command} {' '.join(c.args)}")
            return None
        name = args[1]
        if name in acp_manager.list_connected():
            console.print(f"[green]Already connected to '{name}'[/green]")
            return "connected"
        try:
            session_id = await acp_manager.connect(name)
            console.print(f"[green]✓[/green] Connected to '{name}' (ACP session {session_id[:8]})")
            return "connected"
        except Exception as e:
            console.print(f"[red]Failed to connect: {e}[/red]")
            return None

    if sub == "disconnect":
        active = acp_manager.active_session()
        if active:
            await acp_manager.disconnect(active.name)
            console.print(f"[green]✓[/green] Disconnected from '{active.name}'")
            return "disconnected"
        console.print("[yellow]Not connected to any ACP agent[/yellow]")
        return None

    if sub == "list":
        connected = acp_manager.list_connected()
        active = acp_manager.active_session()
        if not connected:
            console.print("No connected ACP agents.")
        else:
            lines = ["Connected ACP agents:"]
            for name in connected:
                marker = "→" if active and active.name == name else " "
                lines.append(f"  {marker} {name}")
            console.print("\n".join(lines))
        return None

    if sub == "configs":
        configs = acp_manager._registry.list_all()
        if not configs:
            console.print("No registered ACP agents. Use '/acp register <name> <command> [args...]'")
        else:
            lines = ["Registered ACP agents:"]
            for c in configs:
                args_str = " ".join(c.args) if c.args else ""
                cref = f" [{c.credentials_ref}]" if c.credentials_ref else ""
                lines.append(f"  {c.name:<20} {c.command} {args_str}{cref}")
            console.print("\n".join(lines))
        return None

    console.print(f"Unknown acp subcommand: {sub!r}. Use register, connect, disconnect, list, or configs.")
    return None


def handle_tokens(tracker: Any, model: str, prices: Any, console: Any) -> None:
    """Print cumulative token usage and estimated cost for the current session."""
    totals = tracker.totals()
    hit_rate = tracker.cache_hit_rate()
    from aede.tokens import estimate_cost
    cost = estimate_cost(
        model=model,
        input_tokens=totals["input_tokens"],
        output_tokens=totals["output_tokens"],
        cached_tokens=totals["cached_tokens"],
        prices=prices,
    )
    console.print(f"Session token usage")
    console.print(f"  Input:    {totals['input_tokens']:>10,}    Cached: {totals['cached_tokens']:>10,}  ({hit_rate:.1%} hit rate)")
    console.print(f"  Output:   {totals['output_tokens']:>10,}")
    if cost is not None:
        console.print(f"\n  Est. cost: ~${cost:.4f}  (OpenRouter pricing · may differ slightly from direct API)")
    else:
        console.print(f"\n  Est. cost: (price unavailable for model {model!r})")


def handle_config_show(cfg: Any, console: Any) -> None:
    """Print the effective merged configuration (global + project overrides)."""
    lines = ["Effective config  (global + project)"]
    fields = [
        ("model", cfg.model),
        ("compaction_threshold", cfg.compaction_threshold),
        ("tool_output_max_tokens", cfg.tool_output_max_tokens),
        ("shell", cfg.shell),
        ("batch_approval_max", cfg.batch_approval_max),
        ("auto_approve", ", ".join(cfg.auto_approve) if cfg.auto_approve else "(none)"),
    ]
    mcp_servers = getattr(cfg, "mcp_servers", {})
    mcp_count = len(mcp_servers)
    fields.append(("mcp_servers", f"{mcp_count} configured" if mcp_count else "(none)"))
    for k, v in fields:
        source = cfg.sources.get(k, "default")
        lines.append(f"  {k:<30} {v:<25} [{source}]")
    console.print("\n".join(lines))


def handle_config_edit(
    args: list[str],
    cfg: Any,
    console: Any,
    home: Path,
    project_dir: Path,
) -> None:
    """Handle editing config file or values via /config commands.

    Usage:
      /config global|project
      /config raw [project]       — open raw YAML config in editor
      /config <scope> <key> <value>
      /config <scope> auto_approve add/remove <tool>
    """
    if not args:
        handle_config_show(cfg, console)
        return

    from aede.config import DEFAULT_CONFIG, write_config_value, edit_config_file

    scope = args[0].lower()

    if scope == "raw":
        target = args[1].lower() if len(args) > 1 else "global"
        if target not in ("global", "project"):
            console.print("[red]Error: target must be 'global' or 'project'[/red]")
            return
        try:
            edit_config_file(target, home=home, project_dir=project_dir)
            console.print(f"[green]✓[/green] Opened raw {target} config in editor.")
        except Exception as e:
            console.print(f"[red]Error launching editor: {e}[/red]")
        return

    if scope not in ("global", "project"):
        console.print("[red]Error: Scope must be 'global' or 'project'[/red]")
        return

    if len(args) == 1:
        try:
            edit_config_file(scope, home=home, project_dir=project_dir)
            console.print(f"[green]✓[/green] Opened {scope} config file in editor.")
        except Exception as e:
            console.print(f"[red]Error launching editor: {e}[/red]")
        return

    if len(args) >= 4 and args[1].lower() == "auto_approve" and args[2].lower() in ("add", "remove"):
        action = args[2].lower()
        tool = args[3].lower()
        try:
            write_config_value(scope=scope, key="auto_approve", value=tool, action=action, home=home, project_dir=project_dir)
            console.print(f"[green]✓[/green] auto_approve list updated (removed/added {tool}) in {scope} config.")
        except Exception as e:
            console.print(f"[red]Error updating config: {e}[/red]")
        return

    if len(args) >= 3:
        key = args[1].lower()
        value = args[2]
        if key not in DEFAULT_CONFIG:
            console.print(f"[red]Error: Unknown config key {key!r}[/red]")
            return
        try:
            write_config_value(scope=scope, key=key, value=value, home=home, project_dir=project_dir)
            console.print(f"[green]✓[/green] {key} set to {value!r} in {scope} config.")
        except Exception as e:
            console.print(f"[red]Error setting config: {e}[/red]")
        return

    console.print(
        "Usage:\n"
        "  /config [global|project]              — open config file in $EDITOR\n"
        "  /config raw [project]                 — open raw YAML config in editor\n"
        "  /config <scope> <key> <value>         — set config key inline\n"
        "  /config <scope> auto_approve add/remove <tool> — update auto-approve list"
    )


ACP_COMMANDS = {
    "codex": ("npx", ["-y", "@agentclientprotocol/codex-acp"]),
    "codex/gpt-5.5": ("npx", ["-y", "@agentclientprotocol/codex-acp"]),
    "codex/gpt-5.3-codex": ("npx", ["-y", "@agentclientprotocol/codex-acp"]),
    "codex/o3": ("npx", ["-y", "@agentclientprotocol/codex-acp"]),
    "codex/o4-mini": ("npx", ["-y", "@agentclientprotocol/codex-acp"]),
    "claude-code": ("npx", ["-y", "@agentclientprotocol/claude-agent-acp"]),
    "claude-code/fable-5": ("npx", ["-y", "@agentclientprotocol/claude-agent-acp"]),
    "claude-code/opus-4-8": ("npx", ["-y", "@agentclientprotocol/claude-agent-acp"]),
    # "claude-code/opus-4-7": ("npx", ["-y", "@agentclientprotocol/claude-agent-acp"]),
    "claude-code/sonnet-4-6": ("npx", ["-y", "@agentclientprotocol/claude-agent-acp"]),
    "claude-code/haiku-4-5": ("npx", ["-y", "@agentclientprotocol/claude-agent-acp"]),
    "gemini": ("gemini", ["--acp"]),
    "agy": ("agy", ["--acp"]),
    "agy/gemini-3-5-flash": ("agy", ["--acp"]),
    "agy/gemini-3-1-pro": ("agy", ["--acp"]),
    "agy/claude-sonnet-4-6": ("agy", ["--acp"]),
    "agy/claude-opus-4-6": ("agy", ["--acp"]),
    "cline": ("cline", ["--acp"]),
    "cursor": ("cursor-agent", ["--acp"]),
    "goose": ("goose", ["acp"]),
    "goose/anthropic-claude-sonnet-4-6": ("goose", ["acp"]),
    "goose/openai-gpt-4o": ("goose", ["acp"]),

}


def get_acp_model_override(agent_name: str) -> str | None:
    """Get the model override for an ACP agent sub-model entry.
    
    Args:
        agent_name: The agent name (e.g., "claude-code/opus-4-8")
    
    Returns:
        The model override string, or None if not a sub-model entry.
    """
    MODEL_OVERRIDES = {
        "codex/gpt-5.5": "gpt-5.5",
        "codex/gpt-5.3-codex": "gpt-5.3-codex",
        "codex/o3": "o3",
        "codex/o4-mini": "o4-mini",
        "claude-code/fable-5": "claude-fable-5",
        "claude-code/opus-4-8": "claude-opus-4-8",
        # "claude-code/opus-4-7": "claude-opus-4-7",
        "claude-code/sonnet-4-6": "claude-sonnet-4-6",
        "claude-code/haiku-4-5": "claude-haiku-4-5",
        "agy/gemini-3-5-flash": "gemini-3.5-flash",
        "agy/gemini-3-1-pro": "gemini-3.1-pro",
        "agy/claude-sonnet-4-6": "claude-sonnet-4.6-thinking",
        "agy/claude-opus-4-6": "claude-opus-4.6-thinking",
        "goose/anthropic-claude-sonnet-4-6": "anthropic/claude-sonnet-4-6",
        "goose/openai-gpt-4o": "openai/gpt-4o",
    }
    return MODEL_OVERRIDES.get(agent_name)


ACP_CREDENTIALS = {
    "codex": "OPENAI_API_KEY",
    "claude-code": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "cursor": "CURSOR_API_KEY",
}


def credentials_ref_for(agent_name: str) -> str | None:
    base = agent_name.split("/", 1)[0].split("\\", 1)[0]
    return ACP_CREDENTIALS.get(base)


def _masked_prompt(label: str, password: bool = False) -> str:
    from rich.prompt import Prompt
    return Prompt.ask(label, password=password)


async def run_acp_connect(agent_name, vault, registry, console):
    from aede.acp.auth import (
        drive_auth, NeedsKey, NeedsBrowser, NeedsTerminal, Progress, Connected, Failed)
    from aede.acp.client import AcpClient
    client = AcpClient(registry.get(agent_name)) if registry else None
    async for step in drive_auth(agent_name, client=client, vault=vault, registry=registry):
        if isinstance(step, Progress):
            console.print(step.message)
        elif isinstance(step, NeedsKey):
            val = _masked_prompt(f"Enter {step.env_var}", password=True)
            vault.set(step.env_var, val)
        elif isinstance(step, NeedsBrowser):
            console.print("Complete the login in your browser...")
        elif isinstance(step, NeedsTerminal):
            console.print(f"Complete login in the opened terminal: {step.command}")
        elif isinstance(step, Connected):
            console.print(f"[green]✓[/green] connected to {agent_name}")
            return step.session_id
        elif isinstance(step, Failed):
            console.print(f"[red]Failed:[/red] {step.reason}")
            return None


async def handle_setkey(args: list[str], console: Any, home: Path, acp_manager: Any = None) -> None:
    """Persist a credential to the vault and inject it into the current process environment.

    Args:
        args: Expects ``[NAME, value, provider?]``; prints usage help if fewer than 2 items.
        console: Rich Console for output.
        home: aede home directory (Path) where ``credentials.json`` lives.
        acp_manager: Optional AcpManager instance; if given and provider is an ACP
            provider, auto-registers and connects the ACP agent.
    """
    if len(args) < 2:
        console.print("Usage: /setkey <NAME> <value> [provider]")
        console.print("Example: /setkey CODEX_API_KEY sk-or-v1-... codex")
        return
    name = args[0].upper()
    value = args[1]
    provider = args[2].lower() if len(args) > 2 else None

    import os
    from aede.credentials import set_credential
    set_credential(home, name, value, provider)
    os.environ[name] = value

    if provider and acp_manager:
        cmd_info = ACP_COMMANDS.get(provider)
        if cmd_info:
            command, extra_args = cmd_info
            model_override = get_acp_model_override(provider)
            from aede.acp.registry import AgentConfig, AgentTransport
            try:
                acp_manager._registry.get(provider)
            except KeyError:
                try:
                    acp_manager._registry.add(AgentConfig(
                        name=provider,
                        transport=AgentTransport.LOCAL,
                        command=command,
                        args=extra_args,
                        model_override=model_override,
                        credentials_ref=credentials_ref_for(provider),
                    ))
                except ValueError:
                    pass
            try:
                await acp_manager.connect(provider)
                console.print(f"[green]✓[/green] Connected to ACP agent '{provider}'")
            except Exception as e:
                console.print(f"[yellow]Could not connect ACP agent '{provider}': {e}[/yellow]")

    console.print(
        f"[green]✓[/green] {name} saved to ~/.aede/credentials.json and active "
        f"in this session. aede will load it automatically on every future launch. "
        f"(Other already-open terminals are unaffected — this is aede's own "
        f"credential store, not an OS environment variable.)"
    )


def handle_resume(args: list[str], db: Any, console: Any) -> "str | None":
    """Resolve and return the target session id for a /resume command.

    This function only performs resolution — the actual re-entry into a new
    session is handled by ``cli._run``.

    Args:
        args: Either empty (interactive picker) or ``[id_or_prefix]``.
        db: Open ``DB`` instance.
        console: Rich Console (or compatible stub) used for output and input.

    Returns:
        The full session id to resume, or ``None`` if the user cancelled or
        no matching session was found.
    """
    from aede.session import Session

    if args:
        prefix = args[0]
        all_sessions = db.list_sessions(limit=500)
        matches = [r for r in all_sessions if r["id"].startswith(prefix)]
        if len(matches) == 0:
            console.print(f"No session matching {prefix!r}")
            return None
        if len(matches) > 1:
            console.print(f"Ambiguous prefix {prefix!r} — multiple matches:")
            for r in matches:
                console.print(f"  {r['id']}")
            return None
        return matches[0]["id"]

    # Interactive picker
    sessions = Session.list_recent(db=db, limit=20)
    if not sessions:
        console.print("No sessions to resume.")
        return None

    import time
    now = time.time() * 1000
    console.print("Recent sessions:")
    for i, s in enumerate(sessions, 1):
        age_str = _humanize_age(now - s.updated_at)
        title = s.title or "(untitled)"
        console.print(f"  {i:>2}.  {age_str:12}  {title[:60]}")

    raw = console.input("Select session number (blank to cancel): ").strip()
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        console.print("Invalid selection.")
        return None
    if idx < 1 or idx > len(sessions):
        console.print("Selection out of range.")
        return None
    return sessions[idx - 1].id


def handle_delete_session(
    args: list[str],
    db: Any,
    console: Any,
    data_dir: Path,
) -> None:
    """Delete a session from the DB and filesystem.

    Args:
        args: Either empty (interactive picker) or ``[id_or_prefix]``.
        db: Open ``DB`` instance.
        console: Rich Console (or compatible stub) for output.
        data_dir: aede data directory (for cleaning up rollout logs).
    """
    from aede.session import Session

    target_id = None
    if args:
        prefix = args[0]
        all_sessions = db.list_sessions(limit=500)
        matches = [r for r in all_sessions if r["id"].startswith(prefix)]
        if len(matches) == 0:
            console.print(f"No session matching {prefix!r}")
            return
        if len(matches) > 1:
            console.print(f"Ambiguous prefix {prefix!r} — multiple matches:")
            for r in matches:
                console.print(f"  {r['id']}")
            return
        target_id = matches[0]["id"]
    else:
        # Interactive picker
        sessions = Session.list_recent(db=db, limit=20)
        if not sessions:
            console.print("No sessions to delete.")
            return

        import time
        now = time.time() * 1000
        console.print("Recent sessions:")
        for i, s in enumerate(sessions, 1):
            age_str = _humanize_age(now - s.updated_at)
            title = s.title or "(untitled)"
            console.print(f"  {i:>2}.  {age_str:12}  {title[:60]}")

        raw = console.input("Select session number to DELETE (blank to cancel): ").strip()
        if not raw:
            return
        try:
            idx = int(raw)
        except ValueError:
            console.print("Invalid selection.")
            return
        if idx < 1 or idx > len(sessions):
            console.print("Selection out of range.")
            return
        target_id = sessions[idx - 1].id

    if not target_id:
        return

    confirm = console.input(f"Are you sure you want to delete session {target_id[:8]}? [y/N] ").strip().lower()
    if confirm != "y":
        console.print("Cancelled.")
        return

    try:
        session = Session.load(db, target_id)
        session.delete(db)

        # Cleanup rollout logs
        from aede.rollout import Rollout
        # Rollout handles path resolution in __init__
        rollout = Rollout(data_dir / "sessions", target_id)
        if rollout._path.exists():
            rollout._path.unlink()

        # Cleanup notes if they exist
        notes_path = data_dir / "sessions" / f"{target_id}-notes.md"
        if notes_path.exists():
            notes_path.unlink()

        console.print(f"[green]✓[/green] Session {target_id[:8]} deleted.")
    except Exception as e:
        console.print(f"[red]Error deleting session: {e}[/red]")


def handle_serve(
    cfg: Any,
    db: Any,
    console: Any,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Launch the FastAPI backend server."""
    import uvicorn
    from aede.server import app

    app.state.cfg = cfg
    app.state.db = db

    from aede.acp.registry import AgentRegistry as AcpAgentRegistry, seed_default_agents
    from aede.acp.manager import AcpManager
    from aede.acp.credentials import CredentialProvider
    from pathlib import Path
    home = Path(cfg.home)
    acp_registry = AcpAgentRegistry(config_dir=home)
    seed_default_agents(acp_registry)
    app.state.acp_manager = AcpManager(
        registry=acp_registry,
        credential_provider=CredentialProvider(home=home),
    )

    # MCP server bridge
    mcp_servers = getattr(cfg, "mcp_servers", {})
    if mcp_servers:
        try:
            from aede.mcp.client import MCPBridge
            app.state.mcp_bridge = MCPBridge(servers=mcp_servers)
            failed = app.state.mcp_bridge.spawn_all()
            if failed:
                console.print(f"[yellow]⚠ MCP servers failed: {', '.join(failed)}[/yellow]")
            discovered = app.state.mcp_bridge.discovered_tools()
            if discovered:
                console.print(f"[dim]MCP: {len(discovered)} tools from {len(mcp_servers)} servers[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ MCP bridge error: {e}[/yellow]")
    else:
        app.state.mcp_bridge = None

    # Pre-warm ACP agents in parallel if enabled (B3).
    acp_warmup = getattr(cfg, "acp_warmup", True)
    if acp_warmup:
        mgr = app.state.acp_manager
        if mgr:
            from aede.acp.registry import _BASE_AGENTS

            async def _warm_acp():
                tasks = []
                for name, _, _ in _BASE_AGENTS:
                    tasks.append(mgr.connect(name))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for name, result in zip([n for n, _, _ in _BASE_AGENTS], results):
                    if isinstance(result, Exception):
                        logger.debug("ACP warmup failed for %s: %s", name, result)
                        if console:
                            console.print(f"[dim]ACP warmup: {name} — {result}[/dim]")
                    else:
                        if console:
                            console.print(f"[dim]ACP warmup: {name} connected[/dim]")

            asyncio.create_task(_warm_acp())

    console.print(f"[green]Starting aede backend server at http://{host}:{port}[/green]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    # SEC-01: Explicitly bind to 127.0.0.1 by default.
    uvicorn.run(app, host=host, port=port, log_level="info")


def _load_session_notes(data_dir: "Path", session_id: str) -> "str | None":
    """Read the notes file for ``session_id`` from ``data_dir/sessions/``.

    Returns the file contents as a string, or ``None`` if no notes file exists.
    This is the same path ``_maybe_compact`` writes notes to:
    ``data_dir / "sessions" / f"{session_id}-notes.md"``.

    Args:
        data_dir: The aede data directory (``cfg.data_dir``).
        session_id: The session whose notes should be loaded (typically the
            *parent* session when creating a resume branch).

    Returns:
        Notes text or ``None``.
    """
    notes_path = data_dir / "sessions" / f"{session_id}-notes.md"
    if notes_path.exists():
        return notes_path.read_text(encoding="utf-8")
    return None


def _humanize_age(ms: float) -> str:
    """Convert a millisecond age into a human-readable string (e.g. '3h ago')."""
    s = ms / 1000
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)}m ago"
    if s < 86400:
        return f"{int(s // 3600)}h ago"
    return f"{int(s // 86400)}d ago"


def handle_learnings_list(store: Any, console: Any) -> None:
    """Print all learnings in a table."""
    items = store.read_all()
    if not items:
        console.print("No learnings stored.")
        return
    lines = ["Learnings:"]
    for item in items:
        tid = item.get("id", "?")[:8]
        ttype = item.get("type", "?")
        trusted = "✓" if item.get("trusted") else " "
        content = item.get("content", "")[:60]
        lines.append(f"  {tid} [{ttype}] {trusted} {content}")
    console.print("\n".join(lines))


def handle_learnings_show(learning_id: str, store: Any, console: Any) -> None:
    """Print detail for a single learning."""
    items = store.read_all()
    for item in items:
        if item.get("id") == learning_id:
            for k, v in item.items():
                console.print(f"  {k}: {v}")
            return
    console.print(f"Learning {learning_id!r} not found.")


def handle_learnings_delete(learning_id: str, store: Any, console: Any) -> None:
    """Delete a learning by id."""
    if store.delete(learning_id):
        console.print(f"Deleted learning {learning_id[:8]}")
    else:
        console.print(f"Learning {learning_id!r} not found.")


def handle_learnings_edit(learning_id: str, store: Any, console: Any) -> None:
    """Edit a learning by opening $EDITOR on a temp file."""
    import os
    import subprocess
    import tempfile

    items = store.read_all()
    target = None
    for item in items:
        if item.get("id") == learning_id:
            target = item
            break
    if target is None:
        console.print(f"Learning {learning_id!r} not found.")
        return

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(target.get("content", ""))
        tmp_path = f.name

    editor = os.environ.get("EDITOR", "notepad.exe" if os.name == "nt" else "vi")
    from pathlib import Path
    try:
        subprocess.run([editor, tmp_path], check=True)
        new_content = Path(tmp_path).read_text(encoding="utf-8")
        store.update(learning_id, content=new_content)
        console.print(f"Updated learning {learning_id[:8]}")
    except Exception as e:
        console.print(f"Edit error: {e}")
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def handle_import(args: list[str], console: Any, home: Path) -> None:
    """Handle the /import slash-command with subcommands: agent, skill, mcp, all."""
    import argparse
    import shlex

    if not args:
        console.print("[yellow]Usage: /import agent <path> [--source <name>] [--dest <dir>][/yellow]")
        console.print("[yellow]       /import skill <path> [--source <name>] [--dest <dir>][/yellow]")
        console.print("[yellow]       /import mcp <path> [--source <name>] [--dry-run][/yellow]")
        console.print("[yellow]       /import all [--source <name>][/yellow]")
        console.print("[dim]Sources: claude-code, opencode, antigravity, codex, cursor, windsurf[/dim]")
        return

    sub = args[0]
    rest = args[1:]

    if sub == "agent":
        _handle_import_agent(rest, console, home)
    elif sub == "skill":
        _handle_import_skill(rest, console, home)
    elif sub == "mcp":
        _handle_import_mcp(rest, console, home)
    elif sub == "all":
        _handle_import_all(rest, console, home)
    else:
        console.print(f"[red]Unknown import type: {sub!r}[/red]")
        console.print("[yellow]Valid types: agent, skill, mcp, all[/yellow]")


# Sources whose rules/agent files are plain markdown (AGENTS.md / GEMINI.md / .md rules).
_AGENTS_MD_SOURCES = {"antigravity", "codex", "windsurf"}
# Sources whose MCP config is the shared JSON `mcpServers` shape.
_JSON_MCP_SOURCES = {"claude-code", "antigravity", "cursor", "windsurf"}
_IMPORT_SOURCES = {
    "claude-code", "opencode", "antigravity", "codex", "cursor", "windsurf",
}
# Pretty format tag per source slug.
_SOURCE_LABELS = {
    "claude-code": "Claude Code", "opencode": "OpenCode", "antigravity": "Antigravity",
    "codex": "Codex", "cursor": "Cursor", "windsurf": "Windsurf",
}


def _parse_import_args(args: list[str], sub: str) -> argparse.Namespace:
    """Parse args for an import subcommand."""
    import argparse as _argparse
    parser = _argparse.ArgumentParser(prog=f"/import {sub}")
    if sub in ("agent", "skill"):
        parser.add_argument("src", type=Path, help="Source path")
        parser.add_argument("--dest", type=Path, default=None, help="Output directory")
        parser.add_argument("--source", default=None, help="Source harness (auto-detect if omitted)")
    elif sub == "mcp":
        parser.add_argument("path", type=Path, nargs="?", default=None,
                            help="Source MCP config (default: the source's standard path)")
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
        parser.add_argument("--src", type=Path, default=None,
                            help="Source MCP config (alias for the positional path)")
        parser.add_argument("--source", default="claude-code", help="Source harness")
    elif sub == "all":
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
        parser.add_argument("--source", default="claude-code", help="Source harness")
    return parser.parse_args(args)


def _handle_import_agent(args: list[str], console: Any, home: Path) -> None:
    """Import an agent / rules file from any supported source."""
    try:
        ns = _parse_import_args(args, "agent")
    except SystemExit:
        return

    source = ns.source
    if source is not None and source not in _IMPORT_SOURCES:
        console.print(f"[red]Unknown source: {source!r}[/red]")
        console.print(f"[yellow]Valid sources: {', '.join(sorted(_IMPORT_SOURCES))}[/yellow]")
        return

    dest_dir = ns.dest or (home / "agents")
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        report = _import_one_agent(ns.src, dest_dir, source)
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        return

    if report.was_skipped:
        console.print(f"[yellow]Skipped {report.name} (already exists)[/yellow]")
    else:
        console.print(f"[green]Imported {report.name} → {report.dest_path} ({report.format})[/green]")


def _import_one_agent(src: Path, dest_dir: Path, source: str | None, _input_fn=None):
    """Route a single agent/rules file to the right importer based on source/format.

    source=None auto-detects: .mdc → Cursor, plain markdown (AGENTS.md/GEMINI.md/no
    frontmatter) → agents_md, frontmatter .md → Claude Code (fallback OpenCode).
    """
    # Explicit plain-markdown sources (Antigravity/Codex/Windsurf rules).
    if source in _AGENTS_MD_SOURCES:
        from aede.import_.agents_md import import_agents_md
        return import_agents_md(src_path=src, dest_dir=dest_dir,
                                source=_SOURCE_LABELS[source], _input_fn=_input_fn)
    if source == "cursor" or src.suffix == ".mdc":
        from aede.import_.cursor import import_cursor_mdc
        return import_cursor_mdc(src_path=src, dest_dir=dest_dir, _input_fn=_input_fn)
    if source == "opencode":
        from aede.import_.opencode import import_opencode_agent
        return import_opencode_agent(src_path=src, dest_dir=dest_dir, _input_fn=_input_fn)

    text = src.read_text(encoding="utf-8")
    has_frontmatter = text.lstrip().startswith("---")
    if source == "claude-code" or (source is None and has_frontmatter):
        from aede.import_.claude_code import import_claude_code_agent
        try:
            return import_claude_code_agent(src_path=src, dest_dir=dest_dir, _input_fn=_input_fn)
        except Exception:
            if source is None:
                from aede.import_.opencode import import_opencode_agent
                return import_opencode_agent(src_path=src, dest_dir=dest_dir, _input_fn=_input_fn)
            raise

    # Plain markdown with no frontmatter (auto-detected AGENTS.md / GEMINI.md / rules).
    from aede.import_.agents_md import import_agents_md
    label = _SOURCE_LABELS.get(source or "", src.name)
    return import_agents_md(src_path=src, dest_dir=dest_dir, source=label, _input_fn=_input_fn)


def _handle_import_skill(args: list[str], console: Any, home: Path) -> None:
    """Import a Claude Code skill."""
    try:
        ns = _parse_import_args(args, "skill")
    except SystemExit:
        return

    source = ns.source
    if source is not None and source not in _IMPORT_SOURCES:
        console.print(f"[red]Unknown source: {source!r}[/red]")
        console.print(f"[yellow]Valid sources: {', '.join(sorted(_IMPORT_SOURCES))}[/yellow]")
        return

    dest_dir = ns.dest or (home / "skills")
    dest_dir.mkdir(parents=True, exist_ok=True)

    from aede.import_.skills import import_claude_code_skill

    label = _SOURCE_LABELS.get(source or "claude-code", "Claude Code")
    try:
        report = import_claude_code_skill(src_path=ns.src, dest_dir=dest_dir, source=label)
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        return

    if report.was_skipped:
        console.print(f"[yellow]Skipped {report.name} (already exists)[/yellow]")
    else:
        console.print(f"[green]Imported {report.name} → {report.dest_path} ({report.format})[/green]")


# Default MCP config path per source (relative to Path.home()).
_MCP_DEFAULT_PATHS = {
    "claude-code": (".claude", "mcp.json"),
    "antigravity": (".gemini", "config", "mcp_config.json"),
    "codex": (".codex", "config.toml"),
    "cursor": (".cursor", "mcp.json"),
    "windsurf": (".codeium", "windsurf", "mcp_config.json"),
}


def _default_mcp_src(source: str) -> Path:
    parts = _MCP_DEFAULT_PATHS.get(source, (".claude", "mcp.json"))
    return Path.home().joinpath(*parts)


def _handle_import_mcp(args: list[str], console: Any, home: Path) -> None:
    """Import MCP servers from a source's config (JSON shape or Codex TOML)."""
    try:
        ns = _parse_import_args(args, "mcp")
    except SystemExit:
        return

    source = ns.source
    if source not in _IMPORT_SOURCES:
        console.print(f"[red]Unknown source: {source!r}[/red]")
        console.print(f"[yellow]Valid sources: {', '.join(sorted(_IMPORT_SOURCES))}[/yellow]")
        return
    if source == "opencode":
        console.print("[yellow]OpenCode has no MCP config to import[/yellow]")
        return

    src_path = ns.path or ns.src or _default_mcp_src(source)
    if not src_path.exists():
        console.print(f"[yellow]No {_SOURCE_LABELS[source]} MCP config found at {src_path}[/yellow]")
        return

    dest_path = home / "config.yml"
    is_toml = source == "codex" or src_path.suffix == ".toml"

    if ns.dry_run:
        names = _peek_mcp_server_names(src_path, is_toml)
        if not names:
            console.print("[yellow]No MCP servers found in source config[/yellow]")
            return
        console.print(f"[dim]Would import {len(names)} MCP server(s):[/dim]")
        for name in names:
            console.print(f"  • {name}")
        return

    from aede.import_.mcp import import_mcp_from_json, import_mcp_from_toml
    label = _SOURCE_LABELS[source]
    if is_toml:
        reports = import_mcp_from_toml(src_config_path=src_path, dest_config_path=dest_path, source=label)
    else:
        reports = import_mcp_from_json(src_config_path=src_path, dest_config_path=dest_path, source=label)

    if not reports:
        console.print("[yellow]No MCP servers found to import[/yellow]")
        return

    for r in reports:
        if r.was_skipped:
            console.print(f"[yellow]Skipped MCP server: {r.name} (already exists)[/yellow]")
        else:
            console.print(f"[green]Imported MCP server: {r.name}[/green]")


def _peek_mcp_server_names(src_path: Path, is_toml: bool) -> list[str]:
    """List server names in a source MCP config without writing anything."""
    if is_toml:
        import tomllib
        data = tomllib.loads(src_path.read_text(encoding="utf-8"))
        return list((data.get("mcp_servers") or {}).keys())
    import json
    data = json.loads(src_path.read_text(encoding="utf-8"))
    return list((data.get("mcpServers") or {}).keys())


# Per-source default directories for `import all`, relative to Path.home().
# rules: list of (parts, kind) where kind is "file" (single md) or "agents_dir" (*.md glob)
#        or "mdc_dir" (*.mdc glob). skills: dir parts. mcp: handled via _default_mcp_src.
_IMPORT_ALL_LAYOUT = {
    "claude-code": {
        "agents": [((".claude", "agents"), "agents_dir")],
        "skills": (".claude", "skills"),
    },
    "antigravity": {
        "agents": [((".gemini", "AGENTS.md"), "file"), ((".gemini", "GEMINI.md"), "file")],
        "skills": (".gemini", "skills"),
    },
    "codex": {
        "agents": [((".codex", "AGENTS.md"), "file")],
        "skills": (".codex", "skills"),
    },
    "cursor": {
        "agents": [((".cursor", "rules"), "mdc_dir")],
        "skills": None,
    },
    "windsurf": {
        "agents": [((".windsurf", "rules"), "agents_dir")],
        "skills": (".windsurf", "skills"),
    },
}


def _handle_import_all(args: list[str], console: Any, home: Path) -> None:
    """Import everything from a source's standard dirs — agents, skills, MCP servers."""
    try:
        ns = _parse_import_args(args, "all")
    except SystemExit:
        return

    source = ns.source
    if source not in _IMPORT_ALL_LAYOUT:
        console.print(f"[red]Unknown source: {source!r}[/red]")
        console.print(f"[yellow]Valid sources: {', '.join(sorted(_IMPORT_ALL_LAYOUT))}[/yellow]")
        return

    layout = _IMPORT_ALL_LAYOUT[source]
    label = _SOURCE_LABELS[source]
    skip_existing = lambda p: "n"  # noqa: E731 — import-all never overwrites silently
    imported_count = 0
    skipped_count = 0

    # --- Agents / rules ---
    agents_dest = home / "agents"
    agents_dest.mkdir(parents=True, exist_ok=True)
    for parts, kind in layout["agents"]:
        base = Path.home().joinpath(*parts)
        if kind == "file":
            srcs = [base] if base.exists() else []
        elif kind == "agents_dir":
            srcs = sorted(base.glob("*.md")) if base.exists() else []
        elif kind == "mdc_dir":
            srcs = sorted(base.glob("*.mdc")) if base.exists() else []
        else:
            srcs = []
        for src in srcs:
            try:
                report = _import_one_agent(src, agents_dest, source, _input_fn=skip_existing)
                if report.was_skipped:
                    skipped_count += 1
                else:
                    imported_count += 1
                    console.print(f"  [green]Agent: {report.name}[/green]")
            except Exception as e:
                console.print(f"  [red]Agent {src.name}: {e}[/red]")

    # --- Skills (SKILL.md standard) ---
    skills_parts = layout["skills"]
    if skills_parts is None:
        console.print(f"  [dim]{label} has no skills to import[/dim]")
    else:
        skills_dir = Path.home().joinpath(*skills_parts)
        if skills_dir.exists():
            from aede.import_.skills import import_claude_code_skill
            skills_dest = home / "skills"
            skills_dest.mkdir(parents=True, exist_ok=True)
            for child in sorted(skills_dir.iterdir()):
                is_skill = (child.is_dir() and (child / "SKILL.md").exists()) or child.suffix == ".md"
                if not is_skill:
                    continue
                try:
                    report = import_claude_code_skill(
                        src_path=child, dest_dir=skills_dest,
                        source=label, _input_fn=skip_existing,
                    )
                    if report.was_skipped:
                        skipped_count += 1
                    else:
                        imported_count += 1
                        console.print(f"  [green]Skill: {report.name}[/green]")
                except Exception as e:
                    console.print(f"  [red]Skill {child.name}: {e}[/red]")

    # --- MCP servers ---
    mcp_src = _default_mcp_src(source)
    if mcp_src.exists():
        from aede.import_.mcp import import_mcp_from_json, import_mcp_from_toml
        dest_path = home / "config.yml"
        is_toml = source == "codex" or mcp_src.suffix == ".toml"
        importer = import_mcp_from_toml if is_toml else import_mcp_from_json
        try:
            reports = importer(
                src_config_path=mcp_src, dest_config_path=dest_path,
                source=label, _input_fn=skip_existing,
            )
            for r in reports:
                if r.was_skipped:
                    skipped_count += 1
                else:
                    imported_count += 1
                    console.print(f"  [green]MCP server: {r.name}[/green]")
        except Exception as e:
            console.print(f"  [red]MCP import: {e}[/red]")

    console.print(
        f"\nImport complete ({label}): [green]{imported_count} imported[/green], "
        f"[yellow]{skipped_count} skipped[/yellow]"
    )


def handle_extract(
    args: list[str],
    data_dir: Path,
    store: Any,
    verifier: Any,
    console: Any,
    admissibility_llm: Any | None = None,
    model_id: str = "",
    extraction_model_id: str = "",
) -> str | None:
    """Handle ``/extract [session_id]`` — run gated extraction on a past session.

    When called with no arguments, processes the most recent archived session.
    Returns a one-line status string for display.
    """
    from aede.memory.extractor import (
        TraceExtractor, normalize_rollout, gate_candidate,
        _load_rollout,
    )
    from aede.memory.store import LearningsStore

    resolved_store = store or LearningsStore(data_dir)

    # Determine session ID
    session_id: str | None = None
    if args and args[0].strip():
        session_id = args[0].strip()
    else:
        # Find most recent archived session with a rollout file
        sessions_dir = data_dir / "sessions"
        if sessions_dir.exists():
            candidates = []
            for year_dir in sessions_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir():
                            continue
                        for f in day_dir.iterdir():
                            if f.name.startswith("rollout-") and f.suffix == ".jsonl":
                                sid = f.name[len("rollout-"):-len(".jsonl")]
                                candidates.append((f.stat().st_mtime, sid, f))
            if candidates:
                candidates.sort(reverse=True)
                _, session_id, rollout_path = candidates[0]

    if not session_id:
        console.print("[yellow]No session found to extract.[/yellow]")
        return None

    # Find rollout file
    from aede.memory.extractor import ExtractionQueue
    rollout_path = ExtractionQueue._find_rollout(data_dir, session_id)
    if rollout_path is None:
        console.print(f"[yellow]Rollout file not found for session {session_id}.[/yellow]")
        return None

    records = _load_rollout(rollout_path)
    trace = normalize_rollout(records)

    extractor = TraceExtractor(llm=admissibility_llm, model=extraction_model_id or "claude-haiku-4-5")
    candidates = extractor.extract(trace)

    if not candidates:
        console.print(f"[dim]No learnings extracted from {session_id}.[/dim]")
        return f"extracted 0 from {session_id}"

    for cand in candidates:
        if cand.get("provenance") is None:
            cand["provenance"] = {}
        cand["provenance"]["source_session_id"] = session_id

    try:
        existing = resolved_store.list_all() if hasattr(resolved_store, "list_all") else []
    except Exception:
        existing = []

    written = 0
    for cand in candidates:
        result = gate_candidate(
            cand, existing,
            verifier=verifier,
            store=resolved_store,
            admissibility_llm=admissibility_llm,
            model_id=model_id,
            extraction_model_id=extraction_model_id or "claude-haiku-4-5",
        )
        if result.written:
            written += 1
            trust_mark = " (trusted)" if result.trusted else ""
            console.print(f"  [green]✓[/green] {cand['prescriptive_rule'][:80]}{trust_mark}")
        else:
            console.print(f"  [dim]✗ {result.reason}[/dim]")

    console.print(f"[dim]Extracted {written}/{len(candidates)} learnings from {session_id}.[/dim]")
    return f"extracted {written} from {session_id}"


def handle_soul(args: list[str], *, home: Path, console: Any, cfg: Any,
                project_dir: Path | None = None) -> str | None:
    from aede.instructions import SoulDef, load_soul_def
    from aede.config import edit_config_file

    if not args or args[0] == "view":
        s: SoulDef = cfg.soul
        if s.name:
            console.print(f"[bold]Name:[/bold] {s.name}")
        if s.phonetic:
            console.print(f"[bold]Phonetic:[/bold] {s.phonetic}")
        if s.wake_word:
            console.print(f"[bold]Wake word:[/bold] {s.wake_word}")
        if s.wake_word_phonetic:
            console.print(f"[bold]Wake word (phonetic):[/bold] {s.wake_word_phonetic}")
        if s.aliases:
            console.print(f"[bold]Aliases:[/bold] {', '.join(s.aliases)}")
        if s.voice.engine or s.voice.voice_id:
            console.print(f"[bold]Voice:[/bold] engine={s.voice.engine or '—'}, voice_id={s.voice.voice_id or '—'}, rate={s.voice.rate}, pitch={s.voice.pitch}")
        if s.source_files:
            console.print(f"[dim]Sources:[/dim] {', '.join(s.source_files)}")
        if s.persona:
            console.print()
            console.print(s.persona)
        return None

    if args[0] in ("global", "project"):
        if args[0] == "global":
            path = home / "SOUL.md"
        else:
            path = project_dir / "SOUL.md" if project_dir else None
            if path is None:
                console.print("[red]No project directory set[/red]")
                return None
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                frontmatter = load_soul_def(home=home, project_dir=project_dir)
                existing_body = (home / "SOUL.md").read_text(encoding="utf-8") if (home / "SOUL.md").exists() else ""
                body_only = existing_body
                if body_only.startswith("---"):
                    import re as _re
                    m = _re.match(r"\A---\n.*?\n---\n?", body_only, _re.DOTALL)
                    if m:
                        body_only = body_only[m.end():]
                path.write_text(
                    "---\n---\n" + body_only.strip(),
                    encoding="utf-8",
                )
        edit_config_file(path, console)
        return None

    # /soul <key> <value> — write a frontmatter key to project SOUL.md
    if len(args) >= 2:
        key, value = args[0], " ".join(args[1:])
        project_path = (project_dir / "SOUL.md") if project_dir else (home / "SOUL.md")
        project_path.parent.mkdir(parents=True, exist_ok=True)
        text = project_path.read_text(encoding="utf-8") if project_path.exists() else ""
        import re as _re
        m = _re.match(r"\A---\n(.*?)\n---\n?", text, _re.DOTALL)
        if m:
            import yaml
            try:
                existing = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                existing = {}
            body = text[m.end():]
        else:
            existing = {}
            body = text
        existing[key] = value
        lines = ["---"]
        for k, v in existing.items():
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        if body.strip():
            lines.append(body.strip())
        project_path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[green]Set {key} = {value}[/green]")
        return None

    return None
