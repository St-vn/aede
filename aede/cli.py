"""
Entry point and REPL loop for the aede CLI.

Bootstraps configuration and infrastructure (DB, session, rollout, router),
then runs an interactive prompt loop that dispatches slash-commands and
forwards plain text to the AgentLoop.
"""
from __future__ import annotations
import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Any

VERSION = "0.1.0"


def _maybe_set_title(session: Any, db: Any, text: str) -> None:
    """Set the session title from ``text`` if it has not been set yet.

    Calls ``Session.set_title`` exactly once per session.  Subsequent calls
    are no-ops.  Intended to be called after the first user message.

    Args:
        session: The active ``Session`` object (mutated in place).
        db: Open ``DB`` instance.
        text: The first user message from which the title is derived.
    """
    if session.title:
        return
    from aede.session import make_title
    session.set_title(db, make_title(text))


def build_header(model: str, session_id: str) -> str:
    """Return the one-line startup banner shown at the top of each session."""
    short_id = session_id[:4] if len(session_id) >= 4 else session_id
    return f"aede v{VERSION} · {model} · session {short_id}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments. Accepts an optional first task as a positional arg."""
    parser = argparse.ArgumentParser(prog="aede", description="Personal AI agent CLI")
    parser.add_argument("task", nargs="?", default=None, help="Optional first message")
    parser.add_argument("--version", action="version", version=f"aede {VERSION}")
    parser.add_argument("--import", dest="import_action", choices=["claude-code", "opencode"],
                        help="Import an agent from Claude Code or OpenCode")
    parser.add_argument("--src", type=Path, help="Path to the source agent .md file")
    parser.add_argument("--dest", type=Path, default=None, help="Output directory (default: ~/.aede/agents/)")

    # Task 8: serve support
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI backend server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")

    return parser.parse_args(argv)


def main() -> None:
    """Setuptools entry-point: parse args and hand off to the async run loop."""
    args = parse_args()
    if args.import_action:
        _handle_import(args)
        return

    # Support both 'aede serve' and 'aede --serve'
    if args.serve or args.task == "serve":
        _handle_serve_cmd(args)
        return

    asyncio.run(_run(initial_task=args.task))


def _handle_serve_cmd(args: argparse.Namespace) -> None:
    """Handle the ``serve`` command: bootstrap and launch the server."""
    from rich.console import Console
    from aede.config import load_config, bootstrap
    from aede.db import DB
    from aede.commands import handle_serve

    console = Console()
    home = Path(os.environ.get("AEDE_HOME", str(Path.home() / ".aede")))
    bootstrap(home)

    cfg = load_config(home=home, project_dir=Path.cwd())
    db = DB(cfg.data_dir / "aede.db")

    handle_serve(cfg, db, console, host=args.host, port=args.port)


def _handle_import(args: argparse.Namespace) -> None:
    """Handle the ``import`` subcommand synchronously."""
    from rich.console import Console
    console = Console()

    dest_dir = args.dest or (Path.home() / ".aede" / "agents")
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not args.src:
        console.print("[red]Error: --src is required for import[/red]")
        return

    if args.import_action == "claude-code":
        from aede.import_.claude_code import import_claude_code_agent
        report = import_claude_code_agent(src_path=args.src, dest_dir=dest_dir)
    elif args.import_action == "opencode":
        from aede.import_.opencode import import_opencode_agent
        report = import_opencode_agent(src_path=args.src, dest_dir=dest_dir)
    else:
        console.print("[red]Error: unknown import type[/red]")
        return

    if report.was_skipped:
        console.print(f"[yellow]Skipped {report.name} (already exists)[/yellow]")
    else:
        console.print(f"[green]Imported {report.name} → {report.dest_path}[/green]")


async def _run(initial_task: str | None = None, resume_session_id: str | None = None) -> None:
    """Bootstrap all subsystems and run the interactive REPL until exit.

    If ``initial_task`` is provided it is submitted as the first user turn
    before the prompt loop starts.

    If ``resume_session_id`` is provided a new branch session is created whose
    ``parent_id`` points at the given session, and the parent's message history
    is loaded as prior context.  The original session is left intact so it can
    be resumed independently again in the future (branch-aware design).
    """
    from rich.console import Console
    from aede.config import load_config, bootstrap
    from aede.db import DB
    from aede.rollout import Rollout
    from aede.session import Session
    from aede.tools.router import ToolRouter
    from aede.gate import PermissionStore, TerminalGateBackend
    from aede.tokens import TokenTracker, PriceCache
    from aede.agent import AgentLoop
    from aede.commands import parse_command, handle_help, handle_keybinds, handle_sessions, handle_tools, handle_tokens, handle_config_show, handle_config_edit, handle_setkey, handle_resume, handle_skills, handle_agents, _load_session_notes, handle_delete_session

    console = Console()

    home = Path(os.environ.get("AEDE_HOME", str(Path.home() / ".aede")))
    bootstrap(home)

    from aede.credentials import load_credentials_into_env, CredentialsError
    try:
        load_credentials_into_env(home)
    except CredentialsError as e:
        console.print(f"[yellow]⚠ Could not load credentials vault: {e}[/yellow]")

    cfg = load_config(home=home, project_dir=Path.cwd())

    db = DB(cfg.data_dir / "aede.db")

    if resume_session_id is not None:
        # --- Resume path: create a branch session from the parent ---
        try:
            parent = Session.load(db, resume_session_id)
        except KeyError:
            console.print(f"[red]Session not found: {resume_session_id}[/red]")
            return

        session = Session.create(db=db, model=cfg.model, parent_id=parent.id)

        # Reconstruct prior message history from the parent session.
        # Phase-1 limitation: only user/assistant TEXT messages are replayed.
        # tool_use and tool_result content blocks are skipped because replaying
        # them would require reconstructing the full Anthropic multi-part content
        # list (with tool_use_id cross-references), which is not stored in the
        # messages table.  A future phase can persist the raw Anthropic content
        # blocks in the rollout and restore them verbatim.
        parent_rows = db.get_messages(parent.id)
        prior_messages: list[dict] = [
            {"role": r["role"], "content": r["content"]}
            for r in parent_rows
            if r["role"] in ("user", "assistant") and isinstance(r["content"], str)
        ]

        notes = _load_session_notes(cfg.data_dir, parent.id)

        parent_short = parent.id[:8]
        branch_short = session.id[:8]
        console.print(
            f"[dim]Resumed {branch_short} (branch of {parent_short}) "
            f"· {len(prior_messages)} prior messages[/dim]"
        )

        is_resume = True
        session_notes = notes
        rollout_parent_id = parent.id
    else:
        # --- Normal (fresh) path ---
        session = Session.create(db=db, model=cfg.model, parent_id=None)
        prior_messages = None
        is_resume = False
        session_notes = None
        rollout_parent_id = None

    rollout = Rollout(cfg.data_dir / "sessions", session.id)
    rollout.write({"type": "session_start", "session_id": session.id, "parent_id": rollout_parent_id, "model": cfg.model})

    gate_store = PermissionStore()
    gate_store.load_from_config(cfg.auto_approve)

    from aede.skills.loader import load_skills
    skill_registry = load_skills(global_dir=home, project_dir=Path.cwd())
    if skill_registry:
        console.print(f"[dim]Loaded {len(skill_registry)} skills[/dim]")

    from aede.agents.loader import load_agents
    try:
        agent_registry = load_agents(
            global_dir=home,
            project_dir=Path.cwd(),
            skill_registry=skill_registry,
            all_tool_names=["powershell", "read_file", "write_file", "create_file",
                           "list_dir", "search_files", "fetch_url", "web_search"],
        )
        if agent_registry:
            console.print(f"[dim]Loaded {len(agent_registry)} agents[/dim]")
    except Exception as e:
        agent_registry = {}
        console.print(f"[yellow]⚠ Agent load error: {e}[/yellow]")

    router = ToolRouter(
        shell=cfg.shell,
        wsl_distro=cfg.wsl_distro,
        tool_output_max_tokens=cfg.tool_output_max_tokens,
        _cfg=cfg,
        _gate_store=gate_store,
        _agent_registry=agent_registry,
        _session_id=session.id,
    )
    router.set_auto_approved(cfg.auto_approve)

    # MCP server bridge
    mcp_bridge: Any = None
    mcp_servers = getattr(cfg, "mcp_servers", {})
    if mcp_servers:
        try:
            from aede.mcp.client import MCPBridge
            mcp_bridge = MCPBridge(servers=mcp_servers)
            failed = mcp_bridge.spawn_all()
            if failed:
                console.print(f"[yellow]⚠ MCP servers failed to start: {', '.join(failed)}[/yellow]")
            discovered = mcp_bridge.discovered_tools()
            if discovered:
                router._mcp_bridge = mcp_bridge
                router.register_mcp_tools(discovered)
                console.print(f"[dim]MCP: {len(discovered)} tools from {len(mcp_servers)} servers[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ MCP bridge error: {e}[/yellow]")

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
        gate_backend=TerminalGateBackend(
            store=gate_store,
            project_dir=Path.cwd(),
            global_config_path=cfg.home / "config.yml",
            console=console,
        ),
    )
    agent.initialize(
        is_resume=is_resume,
        session_notes=session_notes,
        prior_messages=prior_messages,
        skills=list(skill_registry.values()) if skill_registry else None,
    )

    console.print(build_header(model=cfg.model, session_id=session.id))

    stop_reason = "ctrl_c"
    resume_target: str | None = None

    def _handle_sigint(sig, frame):
        nonlocal stop_reason
        stop_reason = "ctrl_c"
        console.print("\n[dim]Interrupted.[/dim]")
        if mcp_bridge is not None:
            try:
                mcp_bridge.shutdown_all()
            except Exception:
                pass
        _shutdown(session, db, rollout, stop_reason)
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    if initial_task:
        _maybe_set_title(session, db, initial_task)
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
            elif cmd.name == "keybinds":
                handle_keybinds(console)
            elif cmd.name == "sessions":
                handle_sessions(db, console)
            elif cmd.name == "tools":
                handle_tools(router, console)
            elif cmd.name == "tokens":
                handle_tokens(tracker, cfg.model, prices, console)
            elif cmd.name == "config":
                handle_config_edit(cmd.args, cfg, console, home, Path.cwd())
            elif cmd.name == "setkey":
                handle_setkey(cmd.args, console, home)
            elif cmd.name == "compact":
                result = await agent.compact()
                console.print(
                    f"[dim]Compaction done · method: {result['method']} · "
                    f"{result.get('messages_compacted', 0)} messages compacted[/dim]"
                )
            elif cmd.name == "skills":
                handle_skills(skill_registry, console)
            elif cmd.name == "agents":
                handle_agents(agent_registry, console)
            elif cmd.name in ("delete-session", "rm"):
                handle_delete_session(cmd.args, db, console, cfg.data_dir)
            elif cmd.name == "resume":
                target_id = handle_resume(cmd.args, db, console)
                if target_id is not None:
                    resume_target = target_id
                    stop_reason = "resume"
                    break
            continue

        _maybe_set_title(session, db, user_input)
        await _run_turn_safe(agent, user_input, console)

    if mcp_bridge is not None:
        try:
            mcp_bridge.shutdown_all()
        except Exception:
            pass

    _shutdown(session, db, rollout, stop_reason)

    if resume_target is not None:
        return await _run(resume_session_id=resume_target)


async def _run_turn_safe(agent: Any, user_input: str, console: Any) -> None:
    """Run one agent turn, printing any unexpected exception instead of crashing."""
    try:
        await agent.run_turn(user_input)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _shutdown(session: Any, db: Any, rollout: Any, reason: str) -> None:
    """Persist session status, write the session-end rollout record, and close the DB.

    Sessions that exit via /exit or EOF are archived; Ctrl-C leaves them active
    so they can be resumed.

    If a session has no messages, it is deleted entirely from the DB and rollout
    logs to avoid cluttering history with empty runs.
    """
    try:
        # Check if the session is empty
        messages = db.get_messages(session.id, include_compacted=True)
        if not messages:
            # Delete empty session
            session.delete(db)
            # Try to delete the rollout file if it exists
            try:
                if rollout._path.exists():
                    rollout._path.unlink()
            except Exception:
                pass
            db.close()
            return

        status = "active" if reason == "ctrl_c" else "archived"
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
