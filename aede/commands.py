"""
Slash-command parsing and handler functions for the aede REPL.

Recognises ``/command [args...]`` lines typed at the prompt, parses them into
``CommandResult`` values, and implements each handler (help, sessions, tools,
tokens, config, setkey).  The CLI loop in ``cli.py`` calls these handlers
directly.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


COMMANDS = {
    "help", "keybinds", "resume", "sessions", "tools", "config",
    "compact", "tokens", "clear", "exit", "setkey",
    "skills", "agents", "mcp", "delete-session", "rm", "acp", "import",
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
            "  /import agent <path> [--dest]  — import a Claude Code/OpenCode agent",
            "  /import skill <path> [--dest]  — import a Claude Code skill",
            "  /import mcp [--dry-run]        — import MCP servers from Claude Code",
            "  /import all                    — import everything from ~/.claude/",
            "  /acp register <name> <cmd...>  — register an ACP agent",
            "  /acp connect <name>            — connect to an ACP agent (use its subscription as backend)",
            "  /acp disconnect                — disconnect from the ACP agent, return to normal mode",
            "  /acp list                      — show connected ACP agents",
            "  /acp configs                   — show registered ACP agent configs",
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


def handle_acp(args: list[str], acp_manager: Any, console: Any) -> str | None:
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
            session_id = acp_manager.connect(name)
            console.print(f"[green]✓[/green] Connected to '{name}' (ACP session {session_id[:8]})")
            return "connected"
        except Exception as e:
            console.print(f"[red]Failed to connect: {e}[/red]")
            return None

    if sub == "disconnect":
        active = acp_manager.active_session()
        if active:
            acp_manager.disconnect(active.name)
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
      /config <scope> <key> <value>
      /config <scope> auto_approve add/remove <tool>
    """
    if not args:
        handle_config_show(cfg, console)
        return

    scope = args[0].lower()
    if scope not in ("global", "project"):
        console.print("[red]Error: Scope must be 'global' or 'project'[/red]")
        return

    from aede.config import DEFAULT_CONFIG, write_config_value, edit_config_file

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
        "  /config <scope> <key> <value>         — set config key inline\n"
        "  /config <scope> auto_approve add/remove <tool> — update auto-approve list"
    )


ACP_COMMANDS = {
    "codex": ("codex-acp", []),
    "claude-code": ("claude-agent-acp", []),
    "gemini": ("gemini", ["--acp"]),
    "agy": ("agy", ["--acp"]),
    "cline": ("cline", ["--acp"]),
    "cursor": ("cursor-agent", ["--acp"]),
    "goose": ("goose", ["acp"]),
    "opencode": ("opencode", ["--acp"]),
}


def handle_setkey(args: list[str], console: Any, home: Path, acp_manager: Any = None) -> None:
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
                    ))
                except ValueError:
                    pass
            try:
                acp_manager.connect(provider)
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

    from aede.acp.registry import AgentRegistry as AcpAgentRegistry
    from aede.acp.manager import AcpManager
    from aede.acp.credentials import CredentialProvider
    from pathlib import Path
    home = Path(cfg.home)
    acp_registry = AcpAgentRegistry(config_dir=home)
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
        console.print("[yellow]Usage: /import agent <path> [--dest <dir>][/yellow]")
        console.print("[yellow]       /import skill <path> [--dest <dir>][/yellow]")
        console.print("[yellow]       /import mcp [--dry-run][/yellow]")
        console.print("[yellow]       /import all[/yellow]")
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


def _parse_import_args(args: list[str], sub: str) -> argparse.Namespace:
    """Parse args for an import subcommand."""
    import argparse as _argparse
    parser = _argparse.ArgumentParser(prog=f"/import {sub}")
    if sub in ("agent", "skill"):
        parser.add_argument("src", type=Path, help="Source path")
        parser.add_argument("--dest", type=Path, default=None, help="Output directory")
    elif sub == "mcp":
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
        parser.add_argument("--src", type=Path, default=None,
                            help="Source mcp.json (default: ~/.claude/mcp.json)")
    elif sub == "all":
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    return parser.parse_args(args)


def _handle_import_agent(args: list[str], console: Any, home: Path) -> None:
    """Import a Claude Code or OpenCode agent."""
    try:
        ns = _parse_import_args(args, "agent")
    except SystemExit:
        return

    dest_dir = ns.dest or (home / "agents")
    dest_dir.mkdir(parents=True, exist_ok=True)

    from aede.import_.claude_code import import_claude_code_agent
    from aede.import_.opencode import import_opencode_agent

    # Try Claude Code first; if it fails, try OpenCode
    try:
        report = import_claude_code_agent(src_path=ns.src, dest_dir=dest_dir)
    except Exception:
        try:
            report = import_opencode_agent(src_path=ns.src, dest_dir=dest_dir)
        except Exception as e:
            console.print(f"[red]Import failed: {e}[/red]")
            return

    if report.was_skipped:
        console.print(f"[yellow]Skipped {report.name} (already exists)[/yellow]")
    else:
        console.print(f"[green]Imported {report.name} → {report.dest_path}[/green]")


def _handle_import_skill(args: list[str], console: Any, home: Path) -> None:
    """Import a Claude Code skill."""
    try:
        ns = _parse_import_args(args, "skill")
    except SystemExit:
        return

    dest_dir = ns.dest or (home / "skills")
    dest_dir.mkdir(parents=True, exist_ok=True)

    from aede.import_.skills import import_claude_code_skill

    try:
        report = import_claude_code_skill(src_path=ns.src, dest_dir=dest_dir)
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        return

    if report.was_skipped:
        console.print(f"[yellow]Skipped {report.name} (already exists)[/yellow]")
    else:
        console.print(f"[green]Imported {report.name} → {report.dest_path}[/green]")


def _handle_import_mcp(args: list[str], console: Any, home: Path) -> None:
    """Import MCP servers from Claude Code config."""
    try:
        ns = _parse_import_args(args, "mcp")
    except SystemExit:
        return

    src_path = ns.src or (Path.home() / ".claude" / "mcp.json")
    if not src_path.exists():
        console.print(f"[yellow]No Claude Code MCP config found at {src_path}[/yellow]")
        return

    from aede.config import load_config
    cfg = load_config(home=home, project_dir=Path.cwd())
    dest_path = home / "config.yml"

    from aede.import_.mcp import import_mcp_servers_from_claude_code

    if ns.dry_run:
        import json
        import yaml
        src_data = json.loads(src_path.read_text(encoding="utf-8"))
        servers = src_data.get("mcpServers", {})
        if not servers:
            console.print("[yellow]No MCP servers found in source config[/yellow]")
            return
        console.print(f"[dim]Would import {len(servers)} MCP server(s):[/dim]")
        for name in servers:
            console.print(f"  • {name}")
        return

    reports = import_mcp_servers_from_claude_code(
        src_config_path=src_path,
        dest_config_path=dest_path,
    )

    if not reports:
        console.print("[yellow]No MCP servers found to import[/yellow]")
        return

    imported = [r for r in reports if not r.was_skipped]
    skipped = [r for r in reports if r.was_skipped]

    for r in imported:
        console.print(f"[green]Imported MCP server: {r.name}[/green]")
    for r in skipped:
        console.print(f"[yellow]Skipped MCP server: {r.name} (already exists)[/yellow]")


def _handle_import_all(args: list[str], console: Any, home: Path) -> None:
    """Import everything from ~/.claude/ — agents, skills, MCP servers."""
    try:
        ns = _parse_import_args(args, "all")
    except SystemExit:
        return

    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        console.print(f"[yellow]No Claude Code setup detected at {claude_dir}[/yellow]")
        return

    imported_count = 0
    skipped_count = 0

    # Import agents from ~/.claude/agents/ (if it exists) or skill-like agent files
    agents_dir = claude_dir / "agents"
    if agents_dir.exists():
        from aede.import_.claude_code import import_claude_code_agent
        dest_dir = home / "agents"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src in agents_dir.glob("*.md"):
            try:
                report = import_claude_code_agent(
                    src_path=src, dest_dir=dest_dir,
                    _input_fn=lambda p: "n",  # skip existing
                )
                if report.was_skipped:
                    skipped_count += 1
                else:
                    imported_count += 1
                    console.print(f"  [green]Agent: {report.name}[/green]")
            except Exception as e:
                console.print(f"  [red]Agent {src.name}: {e}[/red]")

    # Import skills from ~/.claude/skills/
    skills_dir = claude_dir / "skills"
    if skills_dir.exists():
        from aede.import_.skills import import_claude_code_skill
        dest_dir = home / "skills"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for child in skills_dir.iterdir():
            if child.is_dir():
                skill_file = child / "SKILL.md"
                if skill_file.exists():
                    try:
                        report = import_claude_code_skill(
                            src_path=child, dest_dir=dest_dir,
                            _input_fn=lambda p: "n",
                        )
                        if report.was_skipped:
                            skipped_count += 1
                        else:
                            imported_count += 1
                            console.print(f"  [green]Skill: {report.name}[/green]")
                    except Exception as e:
                        console.print(f"  [red]Skill {child.name}: {e}[/red]")
            elif child.suffix == ".md":
                try:
                    report = import_claude_code_skill(
                        src_path=child, dest_dir=dest_dir,
                        _input_fn=lambda p: "n",
                    )
                    if report.was_skipped:
                        skipped_count += 1
                    else:
                        imported_count += 1
                        console.print(f"  [green]Skill: {report.name}[/green]")
                except Exception as e:
                    console.print(f"  [red]Skill {child.name}: {e}[/red]")

    # Import MCP servers
    mcp_json = claude_dir / "mcp.json"
    if mcp_json.exists():
        from aede.import_.mcp import import_mcp_servers_from_claude_code
        dest_path = home / "config.yml"
        reports = import_mcp_servers_from_claude_code(
            src_config_path=mcp_json,
            dest_config_path=dest_path,
            _input_fn=lambda p: "n",  # skip existing
        )
        for r in reports:
            if r.was_skipped:
                skipped_count += 1
            else:
                imported_count += 1
                console.print(f"  [green]MCP server: {r.name}[/green]")

    console.print(
        f"\nImport complete: [green]{imported_count} imported[/green], "
        f"[yellow]{skipped_count} skipped[/yellow]"
    )
