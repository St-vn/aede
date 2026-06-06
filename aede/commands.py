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
            "  /tools                        — list tools and approval status",
            "  /config [scope] [key] [value] — view or set config",
            "  /compact                      — manually compact context",
            "  /tokens                       — show token usage and cost",
            "  /setkey <NAME> <value>        — save a credential to aede's vault (loaded on every launch)",
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


def handle_setkey(args: list[str], console: Any, home: Path) -> None:
    """Persist a credential to the vault and inject it into the current process environment.

    Args:
        args: Expects ``[NAME, value]``; prints usage help if fewer than 2 items.
        console: Rich Console for output.
        home: aede home directory (Path) where ``credentials.json`` lives.
    """
    if len(args) < 2:
        console.print("Usage: /setkey <NAME> <value>")
        console.print("Example: /setkey OPENROUTER_API_KEY sk-or-v1-...")
        return
    name = args[0].upper()
    value = args[1]

    import os
    from aede.credentials import set_credential
    set_credential(home, name, value)
    os.environ[name] = value

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
