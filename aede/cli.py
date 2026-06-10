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
    """Parse CLI arguments.

    Supports:
    1. ``aede [task]`` — launch the REPL (with optional first message).
    2. ``aede memory <subcommand> [args]`` — synchronous memory management.
    3. ``aede --import claude-code --src ...`` — import agents.
    4. ``aede --serve`` — start the FastAPI backend server.

    Peek at the first argv token to handle ``memory`` subcommand vs positional task.
    """
    effective_argv: list[str] = sys.argv[1:] if argv is None else list(argv)
    first = effective_argv[0] if effective_argv else None

    if first == "memory":
        parser = argparse.ArgumentParser(prog="aede", description="Personal AI agent CLI")
        parser.add_argument("--version", action="version", version=f"aede {VERSION}")
        subparsers = parser.add_subparsers(dest="command")
        mem_parser = subparsers.add_parser("memory", help="Manage stored learnings")
        mem_sub = mem_parser.add_subparsers(dest="memory_subcommand")
        mem_sub.add_parser("list", help="List all learnings")
        show_p = mem_sub.add_parser("show", help="Show one learning by id")
        show_p.add_argument("id", help="Learning id")
        del_p = mem_sub.add_parser("delete", help="Delete a learning by id")
        del_p.add_argument("id", help="Learning id")
        edit_p = mem_sub.add_parser("edit", help="Edit a learning in $EDITOR")
        edit_p.add_argument("id", help="Learning id")
        ns = parser.parse_args(effective_argv)
        if not hasattr(ns, "task"):
            ns.task = None
        return ns
    else:
        parser = argparse.ArgumentParser(prog="aede", description="Personal AI agent CLI")
        parser.add_argument("task", nargs="?", default=None, help="Optional first message")
        parser.add_argument("--version", action="version", version=f"aede {VERSION}")
        parser.add_argument("--import", dest="import_action",
                            choices=["claude-code", "opencode", "antigravity", "codex",
                                     "cursor", "windsurf", "skill", "mcp", "all"],
                            help="Import agents, skills, or MCP servers")
        parser.add_argument("--source", dest="import_source", default=None,
                            help="Source harness for --import all / mcp (e.g. codex, antigravity)")
        parser.add_argument("--src", type=Path, help="Path to the source agent .md file")
        parser.add_argument("--dest", type=Path, default=None, help="Output directory (default: ~/.aede/agents/)")
        parser.add_argument("--serve", action="store_true", help="Start the FastAPI backend server")
        parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
        parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
        ns = parser.parse_args(effective_argv)
        ns.command = None
        return ns


def run_memory_command(argv: list[str], home: Path) -> None:
    """Execute a ``memory`` subcommand synchronously."""
    import sys
    from aede.config import bootstrap, load_config
    from aede.memory.store import LearningsStore

    bootstrap(home)
    cfg = load_config(home=home, project_dir=Path.cwd())
    store = LearningsStore(cfg.data_dir)

    if not argv:
        print("Usage: aede memory {list|show <id>|delete <id>|edit <id>}")
        return

    sub = argv[0]
    if sub == "list":
        _memory_list(store)
    elif sub == "show":
        if len(argv) < 2:
            print("Usage: aede memory show <id>")
            return
        _memory_show(store, argv[1])
    elif sub == "delete":
        if len(argv) < 2:
            print("Usage: aede memory delete <id>")
            return
        _memory_delete(store, argv[1])
    elif sub == "edit":
        if len(argv) < 2:
            print("Usage: aede memory edit <id>")
            return
        _memory_edit(store, argv[1])
    else:
        print(f"Unknown memory subcommand: {sub!r}")


def _memory_list(store: Any) -> None:
    """Print all learnings in a compact tabular form."""
    import json as _json
    records = store.list_all()
    if not records:
        print("No learnings stored.")
        return
    for r in records:
        short_content = r.get("content", "")[:60]
        if len(r.get("content", "")) > 60:
            short_content += "..."
        print(f"{r['id']}  [{r['type']}]  {short_content}")


def _memory_show(store: Any, learning_id: str) -> None:
    """Print the full JSON of one learning."""
    import json as _json
    record = store.get(learning_id)
    if record is None:
        print(f"Error: learning {learning_id!r} not found.")
        return
    print(_json.dumps(record, indent=2, ensure_ascii=False))


def _memory_delete(store: Any, learning_id: str) -> None:
    """Delete one learning by id."""
    removed = store.delete(learning_id)
    if removed:
        print(f"Deleted learning {learning_id!r}.")
    else:
        print(f"Learning {learning_id!r} not found — nothing deleted.")


def _memory_edit(store: Any, learning_id: str) -> None:
    """Open $EDITOR on a temp file containing the learning JSON; write back on save."""
    import json as _json
    import os
    import subprocess
    import tempfile

    record = store.get(learning_id)
    if record is None:
        print(f"Error: learning {learning_id!r} not found.")
        return

    editor = os.environ.get("EDITOR")
    if not editor:
        import sys as _sys
        editor = "notepad.exe" if _sys.platform == "win32" else "vi"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_json.dumps(record, indent=2, ensure_ascii=False))
        tmp_path = Path(tmp.name)

    try:
        subprocess.run([editor, str(tmp_path)])
        try:
            updated = _json.loads(tmp_path.read_text(encoding="utf-8"))
        except _json.JSONDecodeError as exc:
            print(f"Error: edited file is not valid JSON — changes discarded. ({exc})")
            return
        store.update(learning_id, updated)
        print(f"Learning {learning_id!r} updated.")
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def main() -> None:
    """Setuptools entry-point: parse args and hand off to the async run loop."""
    args = parse_args()
    if args.command == "memory":
        home = Path(os.environ.get("AEDE_HOME", str(Path.home() / ".aede")))
        mem_argv = []
        if args.memory_subcommand:
            mem_argv.append(args.memory_subcommand)
            if hasattr(args, "id") and args.id:
                mem_argv.append(args.id)
        run_memory_command(mem_argv, home)
        return
    if args.import_action:
        _handle_import(args)
        return

    if args.serve or (args.task and args.task == "serve"):
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
    home = Path(os.environ.get("AEDE_HOME", str(Path.home() / ".aede")))

    action = args.import_action
    agent_sources = ("claude-code", "opencode", "antigravity", "codex", "cursor", "windsurf")

    if action in agent_sources:
        if not args.src:
            console.print("[red]Error: --src is required for import[/red]")
            return
        dest_dir = args.dest or (home / "agents")
        dest_dir.mkdir(parents=True, exist_ok=True)
        from aede.commands import _import_one_agent
        try:
            report = _import_one_agent(args.src, dest_dir, action)
        except Exception as e:
            console.print(f"[red]Import failed: {e}[/red]")
            return
        if report.was_skipped:
            console.print(f"[yellow]Skipped {report.name} (already exists)[/yellow]")
        else:
            console.print(f"[green]Imported {report.name} → {report.dest_path} ({report.format})[/green]")

    elif action == "skill":
        if not args.src:
            console.print("[red]Error: --src is required for skill import[/red]")
            return
        skill_args = [str(args.src)]
        if args.dest:
            skill_args += ["--dest", str(args.dest)]
        if args.import_source:
            skill_args += ["--source", args.import_source]
        from aede.commands import _handle_import_skill
        _handle_import_skill(skill_args, console, home)

    elif action == "mcp":
        mcp_args = ["--source", args.import_source or "claude-code"]
        if args.src:
            mcp_args += ["--src", str(args.src)]
        from aede.commands import _handle_import_mcp
        _handle_import_mcp(mcp_args, console, home)

    elif action == "all":
        from aede.commands import _handle_import_all
        _handle_import_all(["--source", args.import_source or "claude-code"], console, home)

    else:
        console.print("[red]Error: unknown import type[/red]")


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
    from aede.commands import parse_command, handle_help, handle_keybinds, handle_sessions, handle_tools, handle_tokens, handle_config_show, handle_config_edit, handle_setkey, handle_resume, handle_skills, handle_agents, handle_mcp, handle_acp, _load_session_notes, handle_delete_session, handle_import

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

    # ── ACP (Agent Client Protocol) ──────────────────────────────
    from aede.acp.registry import AgentRegistry as AcpAgentRegistry
    from aede.acp.manager import AcpManager
    from aede.acp.credentials import CredentialProvider

    acp_registry = AcpAgentRegistry(config_dir=home)
    acp_credential_provider = CredentialProvider(home=home)
    acp_manager = AcpManager(
        registry=acp_registry,
        credential_provider=acp_credential_provider,
    )

    router = ToolRouter(
        shell=cfg.shell,
        wsl_distro=cfg.wsl_distro,
        tool_output_max_tokens=cfg.tool_output_max_tokens,
        db=db,
        _cfg=cfg,
        _gate_store=gate_store,
        _agent_registry=agent_registry,
        _session_id=session.id,
        data_dir=cfg.data_dir,
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
        acp_manager=acp_manager,
    )
    agent.initialize(
        is_resume=is_resume,
        session_notes=session_notes,
        prior_messages=prior_messages,
        skills=list(skill_registry.values()) if skill_registry else None,
        initial_task=initial_task,
    )

    console.print(build_header(model=cfg.model, session_id=session.id))

    stop_reason = "ctrl_c"
    stop_requested = False
    resume_target: str | None = None

    def _handle_sigint(sig, frame):
        nonlocal stop_requested
        stop_requested = True
        console.print("\n[dim]Interrupted (will stop after current turn).[/dim]")

    signal.signal(signal.SIGINT, _handle_sigint)

    if initial_task:
        _maybe_set_title(session, db, initial_task)
        await _run_turn_safe(agent, initial_task, console)

    while not stop_requested:
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
                handle_setkey(cmd.args, console, home, acp_manager)
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
            elif cmd.name == "mcp":
                handle_mcp(mcp_servers, console)
            elif cmd.name == "acp":
                handle_acp(cmd.args, acp_manager, console)
            elif cmd.name in ("delete-session", "rm"):
                handle_delete_session(cmd.args, db, console, cfg.data_dir)
            elif cmd.name == "resume":
                target_id = handle_resume(cmd.args, db, console)
                if target_id is not None:
                    resume_target = target_id
                    stop_reason = "resume"
                    break
            elif cmd.name == "import":
                handle_import(cmd.args, console, home)
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
