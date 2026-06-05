from __future__ import annotations
import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Any

VERSION = "0.1.0"


def build_header(model: str, session_id: str) -> str:
    short_id = session_id[:4] if len(session_id) >= 4 else session_id
    return f"jarvis v{VERSION} · {model} · session {short_id}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="jarvis", description="Personal AI agent CLI")
    parser.add_argument("task", nargs="?", default=None, help="Optional first message")
    parser.add_argument("--version", action="version", version=f"jarvis {VERSION}")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    asyncio.run(_run(initial_task=args.task))


async def _run(initial_task: str | None = None) -> None:
    from rich.console import Console
    from jarvis.config import load_config, bootstrap
    from jarvis.db import DB
    from jarvis.rollout import Rollout
    from jarvis.session import Session
    from jarvis.tools.router import ToolRouter
    from jarvis.gate import PermissionStore
    from jarvis.tokens import TokenTracker, PriceCache
    from jarvis.agent import AgentLoop
    from jarvis.commands import parse_command, handle_help, handle_sessions, handle_tools, handle_tokens, handle_config_show, handle_setkey

    console = Console()

    home = Path(os.environ.get("JARVIS_HOME", str(Path.home() / ".jarvis")))
    bootstrap(home)
    cfg = load_config(home=home, project_dir=Path.cwd())

    db = DB(cfg.data_dir / "jarvis.db")
    session = Session.create(db=db, model=cfg.model, parent_id=None)
    rollout = Rollout(cfg.data_dir / "sessions", session.id)
    rollout.write({"type": "session_start", "session_id": session.id, "parent_id": None, "model": cfg.model})

    router = ToolRouter(
        shell=cfg.shell,
        wsl_distro=cfg.wsl_distro,
        tool_output_max_tokens=cfg.tool_output_max_tokens,
    )
    router.set_auto_approved(cfg.auto_approve)

    gate_store = PermissionStore()
    gate_store.load_from_config(cfg.auto_approve)
    tracker = TokenTracker(session_id=session.id, db=db)

    price_cache = PriceCache(home / "cache" / "model_prices.json")
    prices = price_cache.load()

    agent = AgentLoop(
        cfg=cfg,
        session=session,
        db=db,
        rollout=rollout,
        router=router,
        gate_store=gate_store,
        tracker=tracker,
        console=console,
        project_dir=Path.cwd(),
    )
    agent.initialize()

    console.print(build_header(model=cfg.model, session_id=session.id))

    stop_reason = "ctrl_c"

    def _handle_sigint(sig, frame):
        nonlocal stop_reason
        stop_reason = "ctrl_c"
        console.print("\n[dim]Interrupted.[/dim]")
        _shutdown(session, db, rollout, stop_reason)
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    if initial_task:
        await _run_turn_safe(agent, initial_task, console)

    while True:
        try:
            user_input = console.input("> ")
        except EOFError:
            stop_reason = "eof"
            break
        except KeyboardInterrupt:
            stop_reason = "ctrl_c"
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        cmd = parse_command(user_input)
        if cmd is not None:
            if cmd.name == "exit":
                stop_reason = "exit"
                break
            elif cmd.name == "clear":
                confirm = console.input("Start a new session? [y/N] ")
                if confirm.lower() == "y":
                    stop_reason = "exit"
                    break
            elif cmd.name == "help":
                handle_help(console)
            elif cmd.name == "sessions":
                handle_sessions(db, console)
            elif cmd.name == "tools":
                handle_tools(router, console)
            elif cmd.name == "tokens":
                handle_tokens(tracker, cfg.model, prices, console)
            elif cmd.name == "config":
                if not cmd.args:
                    handle_config_show(cfg, console)
                else:
                    console.print("[dim]/config editing not yet implemented in this build[/dim]")
            elif cmd.name == "setkey":
                handle_setkey(cmd.args, console)
            elif cmd.name == "compact":
                console.print("[dim]Manual compaction not yet wired — use /compact after more turns[/dim]")
            elif cmd.name == "resume":
                console.print("[dim]/resume not yet implemented in this build[/dim]")
            continue

        await _run_turn_safe(agent, user_input, console)

    _shutdown(session, db, rollout, stop_reason)


async def _run_turn_safe(agent: Any, user_input: str, console: Any) -> None:
    try:
        await agent.run_turn(user_input)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _shutdown(session: Any, db: Any, rollout: Any, reason: str) -> None:
    status = "active" if reason == "ctrl_c" else "archived"
    try:
        if status == "archived":
            session.archive(db)
        else:
            session.set_active(db)
        rollout.write({"type": "session_end", "status": status})
        db.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
