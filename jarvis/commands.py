from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


COMMANDS = {
    "help", "resume", "sessions", "tools", "config",
    "compact", "tokens", "clear", "exit", "setkey",
}


@dataclass
class CommandResult:
    name: str
    args: list[str] = field(default_factory=list)


def parse_command(text: str) -> CommandResult | None:
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
    console.print(
        "\n".join([
            "Available commands:",
            "  /help                         — this list",
            "  /resume [id]                  — resume a session",
            "  /sessions                     — list recent sessions",
            "  /tools                        — list tools and approval status",
            "  /config [scope] [key] [value] — view or set config",
            "  /compact                      — manually compact context",
            "  /tokens                       — show token usage and cost",
            "  /setkey <NAME> <value>        — set a Windows user env var (persists across shells)",
            "  /clear                        — start a new session",
            "  /exit                         — end session cleanly",
        ])
    )


def handle_sessions(db: Any, console: Any) -> None:
    from jarvis.session import Session
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
    from jarvis.tools.router import GATE_TOOLS
    lines = ["Available tools:"]
    for name in router.tool_names():
        approval = "gate" if name in GATE_TOOLS else "auto"
        allowed = " [always allowed]" if router._session_auto_approve and name in router._session_auto_approve else ""
        lines.append(f"  {name:<20} {approval}{allowed}")
    console.print("\n".join(lines))


def handle_tokens(tracker: Any, model: str, prices: Any, console: Any) -> None:
    totals = tracker.totals()
    hit_rate = tracker.cache_hit_rate()
    from jarvis.tokens import estimate_cost
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


def handle_setkey(args: list[str], console: Any) -> None:
    if len(args) < 2:
        console.print("Usage: /setkey <NAME> <value>")
        console.print("Example: /setkey OPENROUTER_API_KEY sk-or-v1-...")
        return
    name = args[0].upper()
    value = args[1]
    import subprocess, sys
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f'[System.Environment]::SetEnvironmentVariable("{name}", "{value}", "User")'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Failed to set {name}: {result.stderr.strip()}[/red]")
        return
    import os
    os.environ[name] = value
    console.print(f"[green]✓[/green] {name} set (Windows user env + current process). New shells will pick it up automatically.")


def _humanize_age(ms: float) -> str:
    s = ms / 1000
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)}m ago"
    if s < 86400:
        return f"{int(s // 3600)}h ago"
    return f"{int(s // 86400)}d ago"
