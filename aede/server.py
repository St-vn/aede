"""
FastAPI backend server for aede.

Provides REST and WebSocket endpoints for the browser-based UI, including
session management, message history, token usage, and tool-approval gates.
"""
import asyncio
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
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


@app.websocket("/ws/turn")
async def websocket_turn(websocket: WebSocket):
    """Handle interactive agent turns over WebSocket."""
    await websocket.accept()
    
    db = app.state.db
    cfg = app.state.cfg
    
    # Per-connection state
    gate_futures: dict[str, asyncio.Future] = {}
    gate_backend = WebSocketGateBackend(websocket, gate_futures)
    ws_console = WebSocketConsole(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "user_message":
                session_id = data.get("session_id")
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
                )

                # Load prior messages for context
                rows = db.get_messages(session.id)
                prior_messages = [
                    {"role": r["role"], "content": r["content"]}
                    for r in rows
                ]
                agent.initialize(is_resume=True, prior_messages=prior_messages)

                # Run the turn in the background so we can still receive gate responses
                turn_task = asyncio.create_task(agent.run_turn(content))
                
                def on_turn_done(fut):
                    try:
                        fut.result()
                        asyncio.create_task(websocket.send_json({"type": "turn_completed"}))
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


@app.get("/sessions")
async def list_sessions(request: Request):
    """List all sessions from the database."""
    db = request.app.state.db
    return db.list_sessions()


@app.get("/sessions/{session_id}")
async def get_session(request: Request, session_id: str):
    """Get a specific session by ID."""
    db = request.app.state.db
    from aede.session import Session
    try:
        return Session.load(db, session_id).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@app.patch("/sessions/{session_id}")
async def update_session(request: Request, session_id: str, payload: dict):
    """Update session attributes (e.g. title)."""
    db = request.app.state.db
    from aede.session import Session
    try:
        session = Session.load(db, session_id)
        if "title" in payload:
            session.set_title(db, payload["title"])
        return Session.load(db, session_id).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{session_id}")
async def delete_session(request: Request, session_id: str):
    """Delete a session from the DB and filesystem."""
    db = request.app.state.db
    cfg = request.app.state.cfg
    from aede.session import Session
    try:
        session = Session.load(db, session_id)
        session.delete(db)

        # Cleanup rollout logs
        from aede.rollout import Rollout
        rollout = Rollout(cfg.data_dir / "sessions", session_id)
        if rollout._path.exists():
            rollout._path.unlink()

        # Cleanup notes if they exist
        notes_path = cfg.data_dir / "sessions" / f"{session_id}-notes.md"
        if notes_path.exists():
            notes_path.unlink()

        return {"status": "ok"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/messages")
async def get_messages(request: Request, session_id: str):
    """Get message history for a specific session."""
    db = request.app.state.db
    return db.get_messages(session_id)


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
