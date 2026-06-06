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
        lines.append(f"  {k:<30} {v}")
    console.print("\n".join(lines))


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
