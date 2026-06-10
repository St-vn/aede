"""
FastAPI backend server for aede.

Provides REST and WebSocket endpoints for the browser-based UI, including
session management, message history, token usage, and tool-approval gates.
"""
import asyncio
import os
from pathlib import Path
from typing import Any
import sys
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="aede backend")

# ... (middleware same as before)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebSocketGateBackend:
    """Tool-approval backend that sends requests to the Web UI over WebSocket."""

    def __init__(self, websocket: WebSocket, futures: dict[str, asyncio.Future]):
        self._websocket = websocket
        self._futures = futures

    async def request(
        self,
        gate_id: str,
        tool_name: str,
        args: dict[str, Any],
        batch_count: int,
    ) -> tuple[Any, str]:
        from aede.gate import GateDecision
        fut = asyncio.get_running_loop().create_future()
        self._futures[gate_id] = fut
        await self._websocket.send_json({
            "type": "gate_request",
            "gate_id": gate_id,
            "tool_name": tool_name,
            "args": args,
            "batch_count": batch_count,
        })
        try:
            # UI should respond with {"type": "gate_response", "gate_id": "...", "decision": "ALLOW_ONCE", "redirect_msg": ""}
            decision_str, redirect_msg = await fut
            return GateDecision[decision_str], redirect_msg
        finally:
            self._futures.pop(gate_id, None)


class WebSocketConsole:
    """Mock-like console that redirects prints to the Web UI over WebSocket."""

    def __init__(self, websocket: WebSocket):
        self._websocket = websocket

    def print(self, *args, **kwargs):
        """Sends the message as a JSON object to the UI."""
        # Join all args as strings (simple version of rich.console.print)
        text = " ".join(str(a) for a in args)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # print is sync, so we must fire-and-forget the async send
                loop.create_task(self._websocket.send_json({
                    "type": "console_message",
                    "content": text
                }))
        except Exception:
            pass


@app.get("/health")
async def health():
    """Basic health check endpoint."""
    return {"status": "ok"}


@app.websocket("/ws/sessions/{session_id}")
async def websocket_turn(websocket: WebSocket, session_id: str):
    """Handle interactive agent turns for a specific session over WebSocket."""
    await websocket.accept()
    
    db = app.state.db
    cfg = app.state.cfg
    
    gate_futures: dict[str, asyncio.Future] = {}
    gate_backend = WebSocketGateBackend(websocket, gate_futures)
    ws_console = WebSocketConsole(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "user_message":
                content = data.get("content")
                if not session_id or not content:
                    await websocket.send_json({"type": "error", "message": "Missing session_id or content"})
                    continue

                # Bootstrap AgentLoop for this turn
                from aede.session import Session
                from aede.agent import AgentLoop
                from aede.tools.router import ToolRouter
                from aede.gate import PermissionStore
                from aede.tokens import TokenTracker
                from aede.rollout import Rollout

                try:
                    session = Session.load(db, session_id)
                except KeyError:
                    await websocket.send_json({"type": "error", "message": f"Session {session_id} not found"})
                    continue

                # Set session title if it's empty, matching CLI behavior
                if not session.title:
                    from aede.session import make_title
                    session.set_title(db, make_title(content))

                gate_store = PermissionStore()
                gate_store.load_from_config(cfg.auto_approve)

                router = ToolRouter(
                    shell=cfg.shell,
                    wsl_distro=cfg.wsl_distro,
                    tool_output_max_tokens=cfg.tool_output_max_tokens,
                    _cfg=cfg,
                    _gate_store=gate_store,
                    _session_id=session.id,
                )
                router.set_auto_approved(cfg.auto_approve)

                tracker = TokenTracker(session_id=session.id, db=db)
                rollout = Rollout(cfg.data_dir / "sessions", session.id)

                agent = AgentLoop(
                    cfg=cfg,
                    session=session,
                    db=db,
                    rollout=rollout,
                    router=router,
                    gate_store=gate_store,
                    tracker=tracker,
                    console=ws_console,
                    project_dir=Path.cwd(),
                    gate_backend=gate_backend,
                    acp_manager=getattr(app.state, "acp_manager", None),
                )

                # Load prior messages for context
                rows = db.get_messages(session.id)
                prior_messages = [
                    {"role": r["role"], "content": r["content"]}
                    for r in rows
                ]
                agent.initialize(is_resume=True, prior_messages=prior_messages)

                # Resolve @[filename] mentions from the session's project dir
                ws_workspace = Path(session.project_dir).expanduser().resolve() if session.project_dir else None
                resolved_content = _resolve_file_mentions(content, ws_workspace)
                if resolved_content != content:
                    await websocket.send_json({"type": "console_message", "content": "Resolved @ file references"})

                # Run the turn in the background so we can still receive gate responses
                turn_task = asyncio.create_task(agent.run_turn(resolved_content))
                
                def on_turn_done(fut):
                    try:
                        fut.result()
                        asyncio.create_task(websocket.send_json({"type": "turn_completed"}))
                        # Emit context usage info
                        try:
                            if hasattr(agent, 'count_context_tokens'):
                                ctx = agent.count_context_tokens()
                                asyncio.create_task(websocket.send_json({
                                    "type": "context_usage",
                                    "used": ctx.get("total_tokens", 0),
                                    "total": cfg.context_window,
                                }))
                        except Exception:
                            pass
                        # Emit learnings count
                        try:
                            from aede.memory.store import LearningsStore
                            store = LearningsStore(data_dir=cfg.data_dir, db=db)
                            all_l = store.list_all()
                            asyncio.create_task(websocket.send_json({
                                "type": "learnings_injected",
                                "count": len(all_l),
                            }))
                        except Exception:
                            pass
                    except Exception as e:
                        asyncio.create_task(websocket.send_json({"type": "error", "message": str(e)}))

                turn_task.add_done_callback(on_turn_done)

            elif msg_type == "gate_response":
                gate_id = data.get("gate_id")
                decision = data.get("decision")
                redirect_msg = data.get("redirect_msg", "")
                
                if gate_id in gate_futures:
                    gate_futures[gate_id].set_result((decision, redirect_msg))
                else:
                    await websocket.send_json({"type": "error", "message": f"Unknown gate_id: {gate_id}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.post("/api/sessions")
async def create_session(request: Request, payload: dict):
    """Create a new session (optionally as a branch of a parent session)."""
    db = request.app.state.db
    from aede.session import Session
    model = payload.get("model")
    if not model:
        raise HTTPException(status_code=400, detail="model is required")
    session = Session.create(
        db=db,
        model=model,
        parent_id=payload.get("parent_id"),
        project_dir=payload.get("project_dir"),
    )
    return session.to_dict()


@app.get("/api/sessions")
async def list_sessions(request: Request):
    db = request.app.state.db
    return db.list_sessions()


# ── Project endpoints ──────────────────────────────────────────────


@app.post("/api/projects")
async def create_project(request: Request, payload: dict):
    """Register a project directory. Idempotent — returns existing project if path already registered."""
    from aede.project import Project
    db = request.app.state.db
    project_dir = payload.get("project_dir") or payload.get("path")
    if not project_dir:
        raise HTTPException(status_code=400, detail="project_dir is required")
    existing = db.get_project_by_dir(project_dir)
    if existing:
        return Project(existing).to_dict()
    project = Project.create(db=db, project_dir=project_dir)
    return project.to_dict()


@app.get("/api/projects")
async def list_projects(request: Request):
    from aede.project import Project
    db = request.app.state.db
    return [p.to_dict() for p in Project.list_all(db)]


@app.delete("/api/projects/{project_id}")
async def delete_project(request: Request, project_id: str):
    """Remove a project from the list (does NOT touch files on disk)."""
    db = request.app.state.db
    from aede.project import Project
    try:
        project = Project.load(db, project_id)
        project.delete(db)
        return {"status": "ok"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/api/projects/{project_id}/delete-folder")
async def delete_project_folder(request: Request, project_id: str):
    """Remove project from list AND delete the project directory from disk."""
    import shutil
    db = request.app.state.db
    from aede.project import Project
    try:
        project = Project.load(db, project_id)
        path = Path(project.project_dir).expanduser().resolve()
        if path.exists():
            shutil.rmtree(str(path))
        project.delete(db)
        return {"status": "ok"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/api/projects/{project_id}/remove-git")
async def remove_project_git(request: Request, project_id: str):
    """Remove project from list AND delete the .git subdirectory."""
    import shutil
    db = request.app.state.db
    from aede.project import Project
    try:
        project = Project.load(db, project_id)
        git_path = Path(project.project_dir).expanduser().resolve() / ".git"
        if git_path.exists():
            if git_path.is_dir():
                shutil.rmtree(str(git_path))
            else:
                git_path.unlink()
        project.delete(db)
        return {"status": "ok"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.get("/api/sessions/{session_id}")
async def get_session(request: Request, session_id: str):
    db = request.app.state.db
    from aede.session import Session
    try:
        return Session.load(db, session_id).to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@app.patch("/api/sessions/{session_id}")
async def update_session(request: Request, session_id: str, payload: dict):
    db = request.app.state.db
    from aede.session import Session
    try:
        session = Session.load(db, session_id)
        if "title" in payload:
            session.set_title(db, payload["title"])
        if "project_dir" in payload:
            session.set_project_dir(db, payload["project_dir"])
        return Session.load(db, session_id).to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(request: Request, session_id: str):
    db = request.app.state.db
    cfg = request.app.state.cfg
    from aede.session import Session
    try:
        session = Session.load(db, session_id)
        session.delete(db)

        from aede.rollout import Rollout
        rollout = Rollout(cfg.data_dir / "sessions", session_id)
        if rollout._path.exists():
            rollout._path.unlink()

        notes_path = cfg.data_dir / "sessions" / f"{session_id}-notes.md"
        if notes_path.exists():
            notes_path.unlink()

        return {"status": "ok"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _walk_parent_messages(db, session_id: str) -> list[dict]:
    """Recursively collect messages from all ancestor sessions, root-first."""
    from aede.session import Session
    try:
        session = Session.load(db, session_id)
    except KeyError:
        return []
    if not session.parent_id:
        return []
    ancestor_msgs = _walk_parent_messages(db, session.parent_id)
    own = list(db.get_messages(session.parent_id))
    ancestor_msgs.extend(own)
    return ancestor_msgs


@app.get("/api/sessions/{session_id}/messages")
async def get_messages(request: Request, session_id: str):
    """Get message history for a session, including inherited parent messages."""
    db = request.app.state.db
    from aede.session import Session
    try:
        session = Session.load(db, session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    parent_msgs = _walk_parent_messages(db, session_id)
    if parent_msgs:
        parent_msgs[-1]["is_branch_point"] = True
    own = list(db.get_messages(session_id))
    parent_msgs.extend(own)
    return parent_msgs


@app.get("/config")
async def get_config(request: Request):
    """Get the current agent configuration."""
    cfg = request.app.state.cfg
    # Convert AedeConfig to a serializable dict (handling Path objects)
    data = {}
    for k, v in cfg.__dict__.items():
        if isinstance(v, Path):
            data[k] = str(v)
        else:
            data[k] = v
    return data


@app.get("/token_usage")
async def get_token_usage(request: Request, session_id: str | None = None):
    """Get aggregated token usage (global or by session_id)."""
    db = request.app.state.db
    if session_id:
        res = db.get_token_totals(session_id)
        return {
            "total_input_tokens": res["input_tokens"],
            "total_output_tokens": res["output_tokens"],
            "total_cached_tokens": res["cached_tokens"],
        }

    # Global totals
    row = db.con.execute(
        "SELECT SUM(input_tokens) as input_tokens, "
        "SUM(output_tokens) as output_tokens, "
        "SUM(cached_tokens) as cached_tokens FROM token_usage"
    ).fetchone()
    return {
        "total_input_tokens": row["input_tokens"] or 0,
        "total_output_tokens": row["output_tokens"] or 0,
        "total_cached_tokens": row["cached_tokens"] or 0,
    }


# ── Config endpoints ──────────────────────────────────────────


@app.get("/api/config")
async def get_config(request: Request):
    """Return the current merged config as a dict."""
    cfg = request.app.state.cfg
    import dataclasses
    d = {}
    for key in ("model", "context_window", "compaction_threshold", "tool_output_max_tokens",
                 "shell", "wsl_distro", "batch_approval_max", "auto_approve",
                 "api_base_url", "grounding_enabled", "critic_enabled", "critic_model",
                 "critic_api_base_url", "ollama_base_url", "ollama_embed_model",
                 "ollama_timeout_s", "learnings_top_k", "learnings_max_tokens",
                 "reasoning_effort", "thinking_budget"):
        val = getattr(cfg, key, None)
        if val is not None:
            d[key] = val
    d["model_prices"] = cfg.model_prices
    d["mcp_servers"] = cfg.mcp_servers
    return d


@app.get("/api/config/sources")
async def get_config_sources(request: Request):
    """Return the config sources dict showing origin of each key."""
    cfg = request.app.state.cfg
    return cfg.sources


@app.post("/api/config/open")
async def open_config_file(request: Request, payload: dict = {}):
    """Open the config file in the default OS editor."""
    cfg = request.app.state.cfg
    scope = payload.get("scope", "global")
    project_dir = payload.get("project_dir")

    if scope == "global":
        file_path = cfg.home / "config.yml"
    elif scope == "project":
        pdir = Path(project_dir) if project_dir else Path.cwd()
        file_path = pdir / "aede.yml"
    else:
        raise HTTPException(status_code=400, detail="Invalid scope")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Config file not found")

    os.startfile(str(file_path))
    return {"status": "ok"}


@app.get("/api/mcp/servers")
async def list_mcp_servers(request: Request):
    """Return configured MCP servers with real status."""
    cfg = request.app.state.cfg
    bridge = getattr(request.app.state, "mcp_bridge", None)
    servers = {}
    if cfg.mcp_servers:
        for name, srv in cfg.mcp_servers.items():
            running = bridge is not None and hasattr(bridge, "_sessions") and name in bridge._sessions
            tools = []
            if bridge is not None and hasattr(bridge, "_tool_schemas"):
                tools = list(bridge._tool_schemas.get(name, []))
            servers[name] = {
                "command": srv.command,
                "args": srv.args,
                "env": srv.env,
                "trusted": srv.trusted,
                "url": srv.url,
                "enabled": srv.enabled,
                "disabled_tools": srv.disabled_tools,
                "status": "running" if running else "stopped",
                "tools": tools,
            }
    return servers


@app.post("/api/mcp/servers/restart")
async def restart_mcp_servers(request: Request):
    """Restart all MCP servers."""
    _restart_mcp_bridge(request)
    cfg = request.app.state.cfg
    mcp_servers = getattr(cfg, "mcp_servers", {})
    return {"status": "ok", "servers": list(mcp_servers.keys()) if mcp_servers else []}


@app.post("/api/mcp/servers")
async def create_mcp_server(request: Request, payload: dict):
    """Add or update an MCP server in config.yml and restart the bridge."""
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    cfg = request.app.state.cfg
    home = cfg.home
    # Read current config
    import yaml
    cfg_path = home / "config.yml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    mcp_data = data.setdefault("mcp_servers", {})
    mcp_data[name] = {
        "command": payload.get("command", ""),
        "args": payload.get("args", []),
        "env": payload.get("env") or None,
        "url": payload.get("url", ""),
        "trusted": payload.get("trusted", False),
        "enabled": payload.get("enabled", True),
        "disabled_tools": payload.get("disabled_tools", []),
    }
    cfg_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    _restart_mcp_bridge(request)
    return {"status": "ok", "name": name}


@app.put("/api/mcp/servers/{name}")
async def update_mcp_server(name: str, request: Request, payload: dict):
    """Update an existing MCP server's fields (enabled, disabled_tools, etc.) and restart."""
    import yaml
    cfg = request.app.state.cfg
    cfg_path = cfg.home / "config.yml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    mcp_data = data.setdefault("mcp_servers", {})
    if name not in mcp_data:
        raise HTTPException(status_code=404, detail=f"MCP server {name!r} not found")
    entry = mcp_data[name]
    if "enabled" in payload:
        entry["enabled"] = payload["enabled"]
    if "disabled_tools" in payload:
        entry["disabled_tools"] = payload["disabled_tools"]
    cfg_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    _restart_mcp_bridge(request)
    return {"status": "ok", "name": name}


@app.delete("/api/mcp/servers/{name}")
async def delete_mcp_server(name: str, request: Request):
    """Remove an MCP server from config.yml and restart the bridge."""
    import yaml
    cfg = request.app.state.cfg
    cfg_path = cfg.home / "config.yml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    mcp_data = data.setdefault("mcp_servers", {})
    if name not in mcp_data:
        raise HTTPException(status_code=404, detail=f"MCP server {name!r} not found")
    del mcp_data[name]
    cfg_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    _restart_mcp_bridge(request)
    return {"status": "ok", "name": name}


def _restart_mcp_bridge(request: Request) -> None:
    """Helper: reload config, shut down existing bridge, restart with current config."""
    from aede.config import load_config
    request.app.state.cfg = load_config()
    cfg = request.app.state.cfg
    bridge = getattr(request.app.state, "mcp_bridge", None)
    if bridge is not None:
        try:
            bridge.shutdown_all()
        except Exception:
            pass
    mcp_servers = getattr(cfg, "mcp_servers", {})
    if mcp_servers:
        try:
            from aede.mcp.client import MCPBridge
            new_bridge = MCPBridge(servers=mcp_servers)
            new_bridge.spawn_all()
            request.app.state.mcp_bridge = new_bridge
        except Exception:
            request.app.state.mcp_bridge = None
    else:
        request.app.state.mcp_bridge = None


@app.put("/api/config")
async def update_config(request: Request, payload: dict):
    """Update a config value. Payload: {key, value, scope, project_dir?}"""
    key = payload.get("key")
    value = payload.get("value")
    scope = payload.get("scope", "global")
    project_dir = payload.get("project_dir")

    if not key:
        raise HTTPException(status_code=400, detail="key is required")

    if scope == "project" and not project_dir:
        raise HTTPException(status_code=400, detail="project_dir required for project scope")
    from aede.config import write_config_value
    write_config_value(scope=scope, key=key, value=value, project_dir=Path(project_dir) if project_dir else None)

    return {"status": "ok", "key": key, "scope": scope}


# ── Credential endpoints ──────────────────────────────────────


@app.get("/api/credentials")
async def list_credentials(request: Request):
    """Return all credential names and providers (without values).

    Reads from ``~/.aede/credentials.json`` via ``aede.credentials``.
    """
    cfg = request.app.state.cfg
    from aede.credentials import list_credentials as _list
    return _list(cfg.home)


ACP_COMMANDS = {
    "codex": ("codex-acp", []),
    "codex/gpt-5.5": ("codex-acp", []),
    "codex/gpt-5.3-codex": ("codex-acp", []),
    "codex/o3": ("codex-acp", []),
    "codex/o4-mini": ("codex-acp", []),
    "claude-code": ("claude-agent-acp", []),
    "claude-code/fable-5": ("claude-agent-acp", []),
    "claude-code/opus-4-8": ("claude-agent-acp", []),
    "claude-code/opus-4-7": ("claude-agent-acp", []),
    "claude-code/sonnet-4-6": ("claude-agent-acp", []),
    "claude-code/haiku-4-5": ("claude-agent-acp", []),
    "gemini": ("gemini", ["--acp"]),
    "agy": ("agy", ["--acp"]),
    "agy/gemini-3-5-flash": ("agy", ["--acp"]),
    "agy/claude-sonnet-4-6": ("agy", ["--acp"]),
    "agy/claude-opus-4-6": ("agy", ["--acp"]),
    "cline": ("cline", ["--acp"]),
    "cursor": ("cursor-agent", ["--acp"]),
    "goose": ("goose", ["acp"]),
    "goose/anthropic-claude-sonnet-4-6": ("goose", ["acp"]),
    "goose/openai-gpt-4o": ("goose", ["acp"]),
    "opencode": ("opencode", ["--acp"]),
}


@app.post("/api/credentials")
async def create_credential(request: Request, payload: dict):
    """Create or update a credential in the vault file and current env."""
    cfg = request.app.state.cfg
    from aede.credentials import set_credential as _set
    name = payload.get("name")
    value = payload.get("value")
    provider = payload.get("provider")
    if not name or not value:
        raise HTTPException(status_code=400, detail="name and value are required")
    import os
    _set(cfg.home, name, value, provider)
    os.environ[name] = value

    acp_connected = False
    if provider:
        mgr = getattr(request.app.state, "acp_manager", None)
        if mgr:
            cmd_info = ACP_COMMANDS.get(provider)
            if cmd_info:
                command, args = cmd_info
                from aede.commands import get_acp_model_override
                model_override = get_acp_model_override(provider)
                from aede.acp.registry import AgentConfig, AgentTransport
                try:
                    mgr._registry.get(provider)
                except KeyError:
                    try:
                        mgr._registry.add(AgentConfig(
                            name=provider,
                            transport=AgentTransport.LOCAL,
                            command=command,
                            args=args,
                            model_override=model_override,
                        ))
                    except ValueError:
                        pass
                try:
                    mgr.connect(provider)
                    acp_connected = True
                except Exception:
                    pass

    return {"status": "ok", "name": name, "acp_connected": acp_connected}


@app.delete("/api/credentials/{name}")
async def delete_credential(request: Request, name: str):
    """Delete a credential from the vault file and current env."""
    cfg = request.app.state.cfg
    from aede.credentials import delete_credential as _del, list_credentials as _list
    creds = {c["name"]: c.get("provider") for c in _list(cfg.home)}
    provider = creds.get(name)
    _del(cfg.home, name)
    import os
    os.environ.pop(name, None)

    if provider:
        mgr = getattr(request.app.state, "acp_manager", None)
        if mgr and provider in ACP_COMMANDS:
            mgr.disconnect(provider)
            try:
                mgr._registry.remove(provider)
            except (KeyError, ValueError):
                pass

    return {"status": "ok"}


# ── Learnings endpoints ───────────────────────────────────────


def _get_learnings_store(request: Request):
    """Lazy-init LearningsStore from request state."""
    if not hasattr(request.app.state, 'learnings_store') or request.app.state.learnings_store is None:
        from aede.memory.store import LearningsStore
        request.app.state.learnings_store = LearningsStore(
            data_dir=request.app.state.cfg.data_dir,
            db=request.app.state.db,
        )
    return request.app.state.learnings_store


@app.get("/api/learnings")
async def list_learnings(request: Request):
    """Return all learnings from the store."""
    store = _get_learnings_store(request)
    return store.list_all()


@app.post("/api/learnings")
async def create_learning(request: Request, payload: dict):
    """Create a new learning."""
    store = _get_learnings_store(request)
    record = store.write_learning(
        type=payload.get("type", "config-correction"),
        content=payload.get("content", ""),
        source=payload.get("source", "user"),
        source_session_id=payload.get("source_session_id", ""),
        trusted=payload.get("trusted", True),
    )
    return record


@app.delete("/api/learnings/{learning_id}")
async def delete_learning(request: Request, learning_id: str):
    """Delete a learning."""
    store = _get_learnings_store(request)
    success = store.delete(learning_id)
    if not success:
        raise HTTPException(status_code=404, detail="Learning not found")
    return {"status": "ok"}


# ── Agents / Skills endpoints ─────────────────────────────────

_PHASE1_TOOLS = ["powershell", "read_file", "write_file", "create_file",
                 "list_dir", "search_files", "fetch_url", "web_search",
                 "session_search", "write_learning", "subagent"]


def _get_agent_registry(request: Request) -> dict:
    if not hasattr(request.app.state, 'agent_registry'):
        from aede.agents.loader import load_agents
        from aede.skills.loader import load_skills
        home = request.app.state.cfg.home
        skill_registry = _get_skill_registry(request)
        request.app.state.agent_registry = load_agents(
            global_dir=home,
            project_dir=home,
            skill_registry=skill_registry,
            all_tool_names=_PHASE1_TOOLS,
        )
    return request.app.state.agent_registry


def _get_skill_registry(request: Request) -> dict:
    if not hasattr(request.app.state, 'skill_registry'):
        from aede.skills.loader import load_skills
        home = request.app.state.cfg.home
        request.app.state.skill_registry = load_skills(global_dir=home, project_dir=home)
    return request.app.state.skill_registry


_AGENT_UPLOAD_EXTS = (".md", ".agent")


def _resolve_agent_path(home: Path, name: str, scope: str = "global", project_dir: str | None = None) -> Path:
    if scope == "project" and project_dir:
        return Path(project_dir) / "agents" / f"{name}.md"
    return home / "agents" / f"{name}.md"


def _resolve_skill_path(home: Path, name: str, scope: str = "global", project_dir: str | None = None) -> Path:
    if scope == "project" and project_dir:
        return Path(project_dir) / "skills" / f"{name}.md"
    return home / "skills" / f"{name}.md"


@app.post("/api/agents/upload")
async def upload_agent(request: Request, file: UploadFile = File(...)):
    """Upload an agent .md or .agent file and save it to the agents directory."""
    if not file.filename or not any(file.filename.lower().endswith(e) for e in _AGENT_UPLOAD_EXTS):
        raise HTTPException(status_code=400, detail="Only .md and .agent files are accepted")
    content = (await file.read()).decode("utf-8")
    if not content.startswith("---"):
        raise HTTPException(status_code=400, detail="File must start with YAML frontmatter (---)")
    from aede.agents.schema import AgentDef, AgentLoadError
    import tempfile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
    try:
        tmp.write(content)
        tmp.close()
        ad = AgentDef.from_file(Path(tmp.name))
    except AgentLoadError as e:
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    home = request.app.state.cfg.home
    scope = request.query_params.get("scope", "global")
    project_dir = request.query_params.get("project_dir")
    dest = _resolve_agent_path(home, ad.name, scope, project_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=f"Agent {ad.name!r} already exists")
    Path(tmp.name).rename(dest)
    request.app.state.agent_registry = None
    return {"status": "ok", "name": ad.name}


@app.get("/api/agents")
async def list_agents(request: Request):
    """Return list of available agents."""
    registry = _get_agent_registry(request)
    home = request.app.state.cfg.home
    agents = []
    for name, ad in registry.items():
        fp = ad.source_path or home / "agents" / f"{name}.md"
        scope = "global" if str(fp).startswith(str(home)) else "project"
        agents.append({
            "name": name,
            "description": ad.description,
            "model": ad.model,
            "skills": ad.skills,
            "tools": ad.tools,
            "disallowed_tools": ad.disallowed_tools,
            "max_turns": ad.max_turns,
            "system_prompt": ad.system_prompt,
            "body": ad.body,
            "file_path": str(fp),
            "scope": scope,
        })
    return agents


@app.post("/api/agents")
async def create_agent(request: Request, payload: dict):
    """Create a new agent definition file."""
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    home = request.app.state.cfg.home
    scope = payload.get("scope", "global")
    project_dir = payload.get("project_dir")
    filepath = _resolve_agent_path(home, name, scope, project_dir)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.exists():
        raise HTTPException(status_code=409, detail=f"Agent {name!r} already exists")
    _write_agent_file(filepath, payload)
    request.app.state.agent_registry = None
    return {"status": "ok", "name": name}


@app.put("/api/agents/{name}")
async def update_agent(request: Request, name: str, payload: dict):
    """Update an existing agent definition file."""
    home = request.app.state.cfg.home
    scope = payload.get("scope", "global")
    project_dir = payload.get("project_dir")
    filepath = _resolve_agent_path(home, name, scope, project_dir)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Agent {name!r} not found")
    _write_agent_file(filepath, payload)
    request.app.state.agent_registry = None
    return {"status": "ok", "name": name}


@app.delete("/api/agents/{name}")
async def delete_agent(request: Request, name: str):
    """Delete an agent definition file."""
    home = request.app.state.cfg.home
    scope = request.query_params.get("scope", "global")
    project_dir = request.query_params.get("project_dir")
    filepath = _resolve_agent_path(home, name, scope, project_dir)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Agent {name!r} not found")
    filepath.unlink()
    request.app.state.agent_registry = None
    return {"status": "ok", "name": name}


@app.post("/api/agents/{name}/open")
async def open_agent_file(name: str, request: Request):
    """Open an agent definition file in the default OS editor."""
    home = request.app.state.cfg.home
    scope = request.query_params.get("scope", "global")
    project_dir = request.query_params.get("project_dir")
    filepath = _resolve_agent_path(home, name, scope, project_dir)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Agent {name!r} not found")
    os.startfile(str(filepath))
    return {"status": "ok"}


def _write_agent_file(filepath: Path, payload: dict) -> None:
    import yaml
    frontmatter = {}
    for key in ("name", "description", "model", "skills", "tools", "disallowedTools",
                "disallowed_tools", "maxTurns", "max_turns", "systemPrompt", "system_prompt"):
        if key in payload and payload[key] is not None:
            val = payload[key]
            # Normalize keys to the canonical YAML format
            norm = {"disallowed_tools": "disallowedTools",
                    "max_turns": "maxTurns",
                    "system_prompt": "systemPrompt"}.get(key, key)
            if val != "" and val != [] and val != {}:
                frontmatter[norm] = val
    body = payload.get("body", "")
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).rstrip()
    content = f"---\n{yaml_str}\n---\n"
    if body:
        content += f"\n{body}\n"
    filepath.write_text(content, encoding="utf-8")


_SKILL_UPLOAD_EXTS = (".md", ".skill")


@app.post("/api/skills/upload")
async def upload_skill(request: Request, file: UploadFile = File(...)):
    """Upload a skill .md or .skill file and save it to the skills directory."""
    if not file.filename or not any(file.filename.lower().endswith(e) for e in _SKILL_UPLOAD_EXTS):
        raise HTTPException(status_code=400, detail="Only .md and .skill files are accepted")
    content = (await file.read()).decode("utf-8")
    if not content.startswith("---"):
        raise HTTPException(status_code=400, detail="File must start with YAML frontmatter (---)")
    from aede.skills.schema import SkillDef, SkillLoadError
    import tempfile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
    try:
        tmp.write(content)
        tmp.close()
        sd = SkillDef.from_file(Path(tmp.name))
    except SkillLoadError as e:
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    home = request.app.state.cfg.home
    scope = request.query_params.get("scope", "global")
    project_dir = request.query_params.get("project_dir")
    dest = _resolve_skill_path(home, sd.name, scope, project_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=f"Skill {sd.name!r} already exists")
    Path(tmp.name).rename(dest)
    request.app.state.skill_registry = None
    return {"status": "ok", "name": sd.name}


@app.get("/api/skills")
async def list_skills(request: Request):
    """Return list of available skills."""
    registry = _get_skill_registry(request)
    home = request.app.state.cfg.home
    skills = []
    for sd in registry.values():
        fp = sd.source_path or home / "skills" / f"{sd.name}.md"
        scope = "global" if str(fp).startswith(str(home)) else "project"
        skills.append({
            "name": sd.name,
            "description": sd.description,
            "trigger_phrases": sd.trigger_phrases,
            "allowed_tools": sd.allowed_tools,
            "model": sd.model,
            "body": sd.body,
            "file_path": str(fp),
            "scope": scope,
        })
    return skills


@app.post("/api/skills")
async def create_skill(request: Request, payload: dict):
    """Create a new skill definition file."""
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    home = request.app.state.cfg.home
    scope = payload.get("scope", "global")
    project_dir = payload.get("project_dir")
    filepath = _resolve_skill_path(home, name, scope, project_dir)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if filepath.exists():
        raise HTTPException(status_code=409, detail=f"Skill {name!r} already exists")
    _write_skill_file(filepath, payload)
    request.app.state.skill_registry = None
    return {"status": "ok", "name": name}


@app.put("/api/skills/{name}")
async def update_skill(request: Request, name: str, payload: dict):
    """Update an existing skill definition file."""
    home = request.app.state.cfg.home
    scope = payload.get("scope", "global")
    project_dir = payload.get("project_dir")
    filepath = _resolve_skill_path(home, name, scope, project_dir)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Skill {name!r} not found")
    _write_skill_file(filepath, payload)
    request.app.state.skill_registry = None
    return {"status": "ok", "name": name}


@app.delete("/api/skills/{name}")
async def delete_skill(request: Request, name: str):
    """Delete a skill definition file."""
    home = request.app.state.cfg.home
    scope = request.query_params.get("scope", "global")
    project_dir = request.query_params.get("project_dir")
    filepath = _resolve_skill_path(home, name, scope, project_dir)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Skill {name!r} not found")
    filepath.unlink()
    request.app.state.skill_registry = None
    return {"status": "ok", "name": name}


@app.post("/api/skills/{name}/open")
async def open_skill_file(name: str, request: Request):
    """Open a skill definition file in the default OS editor."""
    home = request.app.state.cfg.home
    scope = request.query_params.get("scope", "global")
    project_dir = request.query_params.get("project_dir")
    filepath = _resolve_skill_path(home, name, scope, project_dir)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Skill {name!r} not found")
    os.startfile(str(filepath))
    return {"status": "ok"}


def _write_skill_file(filepath: Path, payload: dict) -> None:
    import yaml
    frontmatter = {}
    for key in ("name", "description", "trigger_phrases", "allowed_tools", "model"):
        if key in payload and payload[key] is not None:
            val = payload[key]
            if val != "" and val != [] and val != {}:
                frontmatter[key] = val
    body = payload.get("body", "")
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).rstrip()
    content = f"---\n{yaml_str}\n---\n"
    if body:
        content += f"\n{body}\n"
    filepath.write_text(content, encoding="utf-8")


# ── ACP (Agent Client Protocol) endpoints ────────────────────


@app.post("/api/acp/register")
async def acp_register(request: Request, payload: dict):
    """Register a new ACP agent config. Body: {name, command, args?, credentials_ref?}"""
    mgr = getattr(request.app.state, "acp_manager", None)
    if not mgr:
        raise HTTPException(status_code=500, detail="ACP manager not initialized")
    name = payload.get("name")
    command = payload.get("command")
    if not name or not command:
        raise HTTPException(status_code=400, detail="name and command are required")
    from aede.acp.registry import AgentConfig, AgentTransport
    config = AgentConfig(
        name=name,
        transport=AgentTransport.LOCAL,
        command=command,
        args=payload.get("args", []),
        credentials_ref=payload.get("credentials_ref"),
    )
    try:
        mgr._registry.add(config)
        return {"status": "registered", "name": name}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/api/acp/configs")
async def acp_configs(request: Request):
    """Return list of registered ACP agent configs."""
    mgr = getattr(request.app.state, "acp_manager", None)
    if not mgr:
        return {"configs": []}
    configs = []
    for c in mgr._registry.list_all():
        configs.append({
            "name": c.name,
            "command": c.command,
            "args": c.args,
            "credentials_ref": c.credentials_ref,
        })
    return {"configs": configs}


@app.post("/api/acp/connect")
async def acp_connect(request: Request, payload: dict):
    """Connect to an ACP agent. Body: {name}"""
    mgr = getattr(request.app.state, "acp_manager", None)
    if not mgr:
        raise HTTPException(status_code=500, detail="ACP manager not initialized")
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    try:
        session_id = mgr.connect(name)
        return {"status": "connected", "name": name, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/acp/disconnect")
async def acp_disconnect(request: Request, payload: dict):
    """Disconnect from an ACP agent. Body: {name}"""
    mgr = getattr(request.app.state, "acp_manager", None)
    if not mgr:
        raise HTTPException(status_code=500, detail="ACP manager not initialized")
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    mgr.disconnect(name)
    return {"status": "disconnected", "name": name}


@app.get("/api/acp/status")
async def acp_status(request: Request):
    """Return current ACP connection status."""
    mgr = getattr(request.app.state, "acp_manager", None)
    if not mgr:
        return {"connected": False, "active": None, "sessions": []}
    active = mgr.active_session()
    return {
        "connected": active is not None,
        "active": active.name if active else None,
        "sessions": mgr.list_connected(),
    }


# ── Model endpoints ──────────────────────────────────────────


@app.get("/api/models")
async def list_models(request: Request):
    """Return the configured model list (presets + user additions)."""
    from aede.models import load_models
    return load_models(request.app.state.cfg.home)


@app.post("/api/models")
async def add_model(request: Request, payload: dict):
    """Add a custom model. Body: {id, label, provider}"""
    from aede.models import load_models, save_models
    model_id = payload.get("id")
    label = payload.get("label")
    provider = payload.get("provider")
    if not model_id or not label or not provider:
        raise HTTPException(status_code=400, detail="id, label, and provider are required")
    models = load_models(request.app.state.cfg.home)
    models.append({"id": model_id, "label": label, "provider": provider})
    save_models(request.app.state.cfg.home, models)
    return {"status": "ok"}


@app.delete("/api/models/{model_id}")
async def delete_model(request: Request, model_id: str):
    """Remove a model from the list."""
    from aede.models import load_models, save_models
    models = [m for m in load_models(request.app.state.cfg.home) if m["id"] != model_id]
    save_models(request.app.state.cfg.home, models)
    return {"status": "ok"}


@app.put("/api/models")
async def replace_models(request: Request, payload: list):
    """Bulk-replace the model list (for drag reorder or full sync)."""
    from aede.models import save_models
    save_models(request.app.state.cfg.home, payload)
    return {"status": "ok"}


@app.post("/api/models/reset")
async def reset_models(request: Request):
    """Reset the model list to factory presets."""
    from aede.models import reset_models as _reset
    _reset(request.app.state.cfg.home)
    return {"status": "ok"}


# ── Session token detail ──────────────────────────────────────


@app.get("/api/sessions/{session_id}/tokens")
async def get_session_token_detail(request: Request, session_id: str):
    """Return per-turn token usage for a session."""
    db = request.app.state.db
    cfg = request.app.state.cfg
    records = db.get_token_usage_detail(session_id)
    prices = cfg.model_prices
    from aede.tokens import estimate_cost
    total_input = sum(r["input_tokens"] for r in records)
    total_output = sum(r["output_tokens"] for r in records)
    total_cached = sum(r["cached_tokens"] for r in records)
    cost = estimate_cost(cfg.model, total_input, total_output, total_cached, prices)
    return {
        "turns": records,
        "totals": {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cached_tokens": total_cached,
        },
        "estimated_cost_usd": cost,
        "model": cfg.model,
    }


def _resolve_project_root(path: Path | None = None) -> Path | None:
    """Walk up from ``path`` (defaults to CWD) to find the git root."""
    if path is None:
        path = Path.cwd()
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True, text=True, check=True, timeout=5
        )
        return Path(result.stdout.strip())
    except Exception:
        return None





_PICKER_SCRIPT = r"""
import tkinter, sys
from tkinter import filedialog
root = tkinter.Tk()
root.withdraw()
root.attributes("-topmost", True)
try:
    path = filedialog.askdirectory()
    if path:
        sys.stdout.write(path)
except Exception:
    pass
finally:
    root.destroy()
"""


@app.post("/api/workspace/pick-directory")
async def pick_directory():
    """Open a native OS directory picker on the server. Returns the selected path."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-c", _PICKER_SCRIPT],
        capture_output=True, text=True, timeout=120,
    )
    path = result.stdout.strip()
    return {"path": path or None}


@app.post("/api/workspace/browse")
async def browse_workspace(payload: dict = Body(default={"path": ""})):
    """List subdirectories inside a given path for the folder picker."""
    root = Path(payload.get("path", "")).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(status_code=400, detail="Not a valid directory")
    hide_dirs = {".git", "node_modules", ".venv", "__pycache__", ".aede", "build", "dist", ".next", "out"}
    entries = []
    try:
        for p in sorted(root.iterdir()):
            if p.name.startswith(".") or p.name in hide_dirs:
                continue
            if p.is_dir():
                has_git = (p / ".git").is_dir()
                entries.append({
                    "name": p.name,
                    "path": str(p),
                    "has_git": has_git,
                })
    except PermissionError:
        pass
    return {"parent": str(root.parent), "entries": entries}


def _has_project_files(path: Path) -> bool:
    """Check if a directory has recognizable source files."""
    source_exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".json", ".yml", ".yaml", ".toml", ".md"}
    try:
        for p in path.iterdir():
            if p.is_file() and p.suffix in source_exts:
                return True
            if p.is_dir() and p.name not in (".git", "node_modules", ".venv", "__pycache__"):
                return True
        return False
    except Exception:
        return False


import re

_MENTION_RE = re.compile(r"@\[([^\]]+)\]")


def _resolve_file_mentions(content: str, workspace: Path | None = None) -> str:
    """Replace @[filename] markers with actual file content.

    Only resolves mentions when an explicit workspace path is provided.
    Without one (no project selected), @[filename] markers pass through unchanged.
    """
    if not workspace or not _MENTION_RE.search(content):
        return content

    def _replace(m: re.Match) -> str:
        filename = m.group(1)
        filepath = (workspace / filename).resolve()
        try:
            filepath.relative_to(workspace.resolve())
        except ValueError:
            return m.group(0)
        if filepath.is_file() and filepath.stat().st_size < 100_000:
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
                return f"\n```\n# {filename}\n{text}\n```\n"
            except Exception:
                pass
        return m.group(0)

    return _MENTION_RE.sub(_replace, content)


@app.get("/api/workspace/info")
async def get_workspace_info(request: Request, session_id: str | None = None, project_dir: str | None = None):
    """Return metadata about the current workspace/project context.

    Accepts either ``session_id`` (to look up the session's project_dir) or
    a direct ``project_dir`` parameter.  Falls back to the server's CWD.
    """
    from aede.session import Session

    workspace = None
    if project_dir:
        workspace = Path(project_dir).expanduser().resolve()
    elif session_id:
        try:
            session = Session.load(request.app.state.db, session_id)
            if session.project_dir:
                workspace = Path(session.project_dir).expanduser().resolve()
        except (KeyError, Exception):
            pass

    if workspace is None:
        workspace = Path.cwd()

    git_root = _resolve_project_root(workspace)
    project_name = workspace.name if workspace.name not in ("", "/") else None
    has_project = git_root is not None or _has_project_files(workspace)
    return {
        "cwd": str(workspace),
        "git_root": str(git_root) if git_root else None,
        "project_name": project_name,
        "has_project": has_project,
    }


@app.get("/api/workspace/files")
async def get_workspace_files(request: Request, session_id: str | None = None, project_dir: str | None = None):
    """List all tracked and untracked files in the workspace using git with basic walk fallback."""
    from aede.session import Session
    import subprocess
    from pathlib import Path

    workspace = None
    if project_dir:
        workspace = Path(project_dir).expanduser().resolve()
    elif session_id:
        try:
            session = Session.load(request.app.state.db, session_id)
            if session.project_dir:
                workspace = Path(session.project_dir).expanduser().resolve()
        except (KeyError, Exception):
            pass

    repo_dir = _resolve_project_root(workspace) or (workspace or Path.cwd())

    try:
        # Check if .git exists. If not, fallback to directory walk.
        if not (repo_dir / ".git").exists():
            files = []
            ignore_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist"}
            for p in repo_dir.rglob("*"):
                if p.is_file() and not any(part in ignore_dirs for part in p.parts):
                    try:
                        rel = p.relative_to(repo_dir)
                        files.append(str(rel).replace("\\", "/"))
                    except ValueError:
                        continue
            return sorted(files)

        # Run git ls-files to get tracked files
        result_tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True
        )
        tracked = [line.strip() for line in result_tracked.stdout.splitlines() if line.strip()]

        # Run git status --porcelain to get untracked files
        result_untracked = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True
        )
        untracked = []
        for line in result_untracked.stdout.splitlines():
            if line.startswith("?? "):
                file_path = line[3:].strip()
                if (repo_dir / file_path).is_file():
                    untracked.append(file_path)

        all_files = list(set(tracked + untracked))
        return sorted([f.replace("\\", "/") for f in all_files])

    except Exception:
        # Fallback basic walk if anything fails
        files = []
        ignore_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist"}
        for p in repo_dir.rglob("*"):
            if p.is_file() and not any(part in ignore_dirs for part in p.parts):
                try:
                    rel = p.relative_to(repo_dir)
                    files.append(str(rel).replace("\\", "/"))
                except ValueError:
                    continue
        return sorted(files)

