from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Callable, Awaitable
import asyncio
import inspect
import json
import logging
import os
import shutil
import sys
from pathlib import Path

from .registry import AgentConfig, ensure_acp_package

logger = logging.getLogger(__name__)

ACP_PROTOCOL_VERSION = 1

# StreamReader buffer cap for the agent's stdout. ACP NDJSON lines can be large
# (file contents, tool results); the asyncio default of 64 KB overflows.
_STREAM_LIMIT = 16 * 1024 * 1024  # 16 MB


@dataclass
class AgentInfo:
    name: str
    title: str
    version: str


@dataclass
class InitializeResult:
    protocol_version: int
    agent_capabilities: dict
    agent_info: AgentInfo
    auth_methods: list


class AcpError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"ACP error {code}: {message}")


_MAX_FS_BYTES = 10 * 1024 * 1024  # 10 MB hard cap for read/write content


class AcpClient:
    def __init__(
        self,
        config: AgentConfig,
        project_dir: Optional[Path] = None,
        permission_store: Optional[Any] = None,
    ) -> None:
        self._config = config
        self._project_dir: Path | None = project_dir
        self._permission_store = permission_store
        self._proc: asyncio.subprocess.Process | None = None
        self._pending: dict[int | str, asyncio.Future] = {}
        self._next_id = 0
        self._write_lock = asyncio.Lock()
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._session_sinks: dict[str, Callable[[dict], None]] = {}
        self._closed = False
        self._init_result: InitializeResult | None = None
        self._request_handlers: dict[str, Callable[[dict], Awaitable[dict]]] = {}
        self._register_default_handlers()

    # ── lifecycle ──

    def _build_cmd(self) -> list[str]:
        cmd = [self._config.command] + list(self._config.args)
        if self._config.model_override and self._config.name == "codex":
            cmd.extend(["--model", self._config.model_override])

        home_dir = Path.home() / ".aede"
        cached = ensure_acp_package(home_dir, self._config.command, self._config.args)
        if cached is not None:
            cmd = cached

        if sys.platform == 'win32':
            resolved = shutil.which(cmd[0])
            if resolved and resolved.lower().endswith(('.cmd', '.bat')):
                cmd = ['cmd.exe', '/c'] + cmd
        return cmd

    async def start(self, credential_provider=None) -> None:
        cmd = self._build_cmd()
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._inject_env(credential_provider),
            # ACP messages are NDJSON, one object per line, and a single line can
            # be large (tool results, file contents, big session/update chunks).
            # The default StreamReader limit is 64 KB, which overflows on real
            # agent output and crashes the reader with LimitOverrunError.  Raise
            # it so a long line is buffered, not rejected.
            limit=_STREAM_LIMIT,
        )
        self._reader_task = asyncio.ensure_future(self._read_loop())
        self._stderr_task = asyncio.ensure_future(self._stderr_forward())

    async def initialize(self, credential_provider=None) -> InitializeResult:
        await self.start(credential_provider)
        result = await self.send_request("initialize", {
            "protocolVersion": ACP_PROTOCOL_VERSION,
            # Capabilities are a binding contract: the agent only sends a client
            # request for a capability we advertise.  We advertise fs (we handle
            # read/write below) but NOT terminal — the agent runs commands itself.
            # session/request_permission is NOT capability-gated and is always
            # handled (see _register_default_handlers).
            "clientCapabilities": {
                "fs": {"readTextFile": True, "writeTextFile": True},
                "terminal": False,
            },
            "clientInfo": {
                "name": "aede",
                "title": "aede",
                "version": "0.1.0",
            },
        })
        if result["protocolVersion"] != ACP_PROTOCOL_VERSION:
            raise ValueError(
                f"Unsupported protocol version {result['protocolVersion']}: "
                f"aede supports v{ACP_PROTOCOL_VERSION}"
            )
        init_result = InitializeResult(
            protocol_version=result["protocolVersion"],
            agent_capabilities=result.get("agentCapabilities", {}),
            agent_info=AgentInfo(**result["agentInfo"]),
            auth_methods=result.get("authMethods", []),
        )
        self._init_result = init_result
        return init_result

    async def new_session(
        self,
        cwd: str = "",
        mcp_servers: Optional[list] = None,
        timeout: float = 60.0,
        _meta: Optional[dict] = None,
    ) -> str:
        if mcp_servers is None:
            mcp_servers = []
        params: dict = {
            "cwd": cwd,
            "mcpServers": mcp_servers,
        }
        if _meta is not None:
            params["_meta"] = _meta
        try:
            result = await asyncio.wait_for(
                self.send_request("session/new", params),
                timeout=timeout,
            )
        except TimeoutError:
            raise AcpError(-1, f"Agent '{self._config.name}' timed out after {timeout}s")
        return result["sessionId"]

    async def aclose(self) -> None:
        self._closed = True
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(AcpError(-1, "Client closed"))
        self._pending.clear()
        if self._reader_task:
            self._reader_task.cancel()
        if self._stderr_task:
            self._stderr_task.cancel()
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except (AttributeError, ProcessLookupError, TimeoutError):
                try:
                    self._proc.kill()
                    await asyncio.wait_for(self._proc.wait(), timeout=5)
                except (AttributeError, ProcessLookupError, TimeoutError):
                    pass

    # ── core JSON-RPC ──

    async def send_request(self, method: str, params: dict) -> Any:
        if self._closed:
            raise AcpError(-1, "Client is closed")
        rid = self._next_id
        self._next_id += 1
        future = asyncio.get_running_loop().create_future()
        self._pending[rid] = future
        try:
            await self._write({
                "jsonrpc": "2.0",
                "id": rid,
                "method": method,
                "params": params,
            })
            return await future
        except asyncio.CancelledError:
            self._pending.pop(rid, None)
            raise

    async def send_notification(self, method: str, params: dict) -> None:
        await self._write({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        })

    async def _write(self, obj: dict) -> None:
        async with self._write_lock:
            data = json.dumps(obj) + "\n"
            self._proc.stdin.write(data.encode())
            await self._proc.stdin.drain()

    # ── reader loop ──

    async def _read_loop(self) -> None:
        try:
            while not self._closed:
                line = await self._proc.stdout.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("ACP: ignoring non-JSON line from agent: %s", line[:200])
                    continue
                self._dispatch(msg)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("ACP reader error")
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(AcpError(-1, "Reader error"))
        finally:
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(AcpError(-1, "Agent closed connection"))

    async def _stderr_forward(self) -> None:
        try:
            while True:
                line = await self._proc.stderr.readline()
                if not line:
                    break
                if line.strip():
                    logger.debug("ACP stderr: %s", line.rstrip())
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("ACP stderr forwarder crashed")

    def _dispatch(self, msg: dict) -> None:
        has_id = "id" in msg
        has_method = "method" in msg

        if has_method and has_id:
            asyncio.ensure_future(self._handle_inbound_request(msg))
        elif has_method and not has_id:
            asyncio.ensure_future(self._handle_notification(msg))
        elif has_id and not has_method:
            rid = self._norm_id(msg.get("id"))
            future = self._pending.pop(rid, None)
            if future is None:
                logger.warning("ACP response to unknown id %r", msg.get("id"))
                return
            if not future.done():
                error = msg.get("error")
                if error is not None:
                    code = error.get("code", -1) if isinstance(error, dict) else -1
                    message = error.get("message", "unknown error") if isinstance(error, dict) else str(error)
                    future.set_exception(AcpError(code, message))
                elif "result" in msg:
                    future.set_result(msg["result"])
                else:
                    logger.warning("ACP response %r missing both 'error' and 'result'", msg.get("id"))
                    future.set_exception(AcpError(-1, "malformed response: missing error and result"))
        else:
            logger.warning("ACP: skipping malformed message (no id or method): %s", str(msg)[:200])

    @staticmethod
    def _norm_id(rid: Any) -> Any:
        if isinstance(rid, str):
            try:
                return int(rid)
            except ValueError:
                pass
        return rid

    async def _handle_notification(self, msg: dict) -> None:
        params = msg.get("params", {})
        update = params.get("update", {})
        session_id = params.get("sessionId")
        if session_id and session_id in self._session_sinks:
            self._session_sinks[session_id](update)

    async def _handle_inbound_request(self, msg: dict) -> None:
        method = msg.get("method", "")
        params = msg.get("params", {})
        rid = msg.get("id")
        handler = self._request_handlers.get(method)
        if handler:
            try:
                result = handler(params)
                if inspect.isawaitable(result):
                    result = await result
                await self._write({
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": result,
                })
            except Exception as e:
                await self._write({
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {"code": -32603, "message": str(e)},
                })
        else:
            await self._write({
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })

    # ── prompt with streaming + cancel ──

    async def prompt(
        self,
        session_id: str,
        text: str,
        message_id: str = "msg_1",
        on_update: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        accumulated: list[str] = []

        def sink(update: dict) -> None:
            if update.get("sessionUpdate") == "agent_message_chunk":
                content = update.get("content", {})
                if isinstance(content, dict) and content.get("type") == "text":
                    accumulated.append(content.get("text", ""))
            if on_update:
                on_update(update)

        self._session_sinks[session_id] = sink

        try:
            result = await self.send_request("session/prompt", {
                "sessionId": session_id,
                "messageId": message_id,
                "prompt": [{"type": "text", "text": text}],
            })
            result["text"] = "".join(accumulated)
            return result
        finally:
            self._session_sinks.pop(session_id, None)

    async def cancel(self, session_id: str) -> None:
        await self.send_notification("session/cancel", {"sessionId": session_id})

    def set_request_handler(
        self, method: str, handler: Callable[[dict], Awaitable[dict]]
    ) -> None:
        self._request_handlers[method] = handler

    # ── default agent→client request handlers ──
    #
    # The agent sends these reentrant requests DURING a session/prompt turn.
    # Without handlers they get -32601 and the agent stalls the turn forever
    # (no output, no error).  session/request_permission is always required
    # (not capability-gated); fs/* are handled because we advertise fs.

    def _register_default_handlers(self) -> None:
        self._request_handlers.setdefault(
            "session/request_permission", self._default_permission)
        self._request_handlers.setdefault(
            "fs/read_text_file", self._default_fs_read)
        self._request_handlers.setdefault(
            "fs/write_text_file", self._default_fs_write)

    async def _default_permission(self, params: dict) -> dict:
        """Route a tool-permission request through the AcpPermissionBridge gate.

        When a PermissionStore is configured, the bridge is consulted: if the
        tool was already pre-approved (allow_session / allow_project / allow_global)
        the request is allowed; otherwise it is cancelled (no interactive backend
        is available inside an automated handler).

        Without a PermissionStore the handler conservatively returns cancelled so
        the agent can decide how to proceed, rather than blindly selecting allow.

        Returning the correct shape (outcome dict) is required — an incorrect or
        missing shape stalls the agent turn.
        """
        options = params.get("options", []) or []
        tool_call = params.get("toolCall", {}) or {}
        tool_call_id = tool_call.get("toolCallId", "unknown")

        if self._permission_store is not None:
            from .permissions import AcpPermissionBridge, AcpPermissionOutcome
            bridge = AcpPermissionBridge(self._permission_store)

            # Check if already pre-approved in the store
            if self._permission_store.is_allowed(f"acp__{tool_call_id}"):
                # Find an allow option to echo back
                for opt in options:
                    if isinstance(opt, dict) and opt.get("kind") in (
                        "allow_once", "allow_always"
                    ):
                        result = bridge.resolve(
                            tool_call_id=tool_call_id,
                            options=options,
                            choice=opt["optionId"],
                        )
                        if result.outcome == AcpPermissionOutcome.ALLOWED:
                            return {
                                "outcome": {
                                    "outcome": "selected",
                                    "optionId": result.option_id,
                                }
                            }

            # No pre-approval → cancel; no interactive backend available here.
            bridge.resolve_cancelled(tool_call_id)
            return {"outcome": {"outcome": "cancelled"}}

        # No store configured → safe default: cancel the permission request.
        return {"outcome": {"outcome": "cancelled"}}

    async def _default_fs_read(self, params: dict) -> dict:
        raw_path = params.get("path", "")
        p = Path(raw_path).resolve()

        # Sandbox check: path must be inside project_dir when one is set.
        if self._project_dir is not None:
            project_resolved = self._project_dir.resolve()
            try:
                p.relative_to(project_resolved)
            except ValueError:
                raise RuntimeError(
                    f"fs/read_text_file denied: path {p} is outside project_dir "
                    f"{project_resolved}"
                )

        # Permission gate: must be explicitly pre-approved in the store.
        # We use is_allowed() directly rather than tool_action() because
        # tool_action() defaults to "allow" for unknown tool names — which is
        # unsafe for ACP filesystem access.  Only explicit session/project/global
        # grants in the PermissionStore may open a read.
        if self._permission_store is not None:
            if not self._permission_store.is_allowed("acp__fs_read_text_file"):
                raise RuntimeError(
                    "fs/read_text_file denied: no explicit grant in permission store"
                )

        text = p.read_text(encoding="utf-8")

        # Content size cap to prevent memory exhaustion from giant files.
        if len(text.encode("utf-8")) > _MAX_FS_BYTES:
            raise RuntimeError(
                f"fs/read_text_file denied: content exceeds {_MAX_FS_BYTES} byte limit"
            )

        line = params.get("line")
        limit = params.get("limit")
        if line is not None or limit is not None:
            lines = text.splitlines(keepends=True)
            start = (line - 1) if isinstance(line, int) and line > 0 else 0
            end = (start + limit) if isinstance(limit, int) else None
            text = "".join(lines[start:end])
        return {"content": text}

    async def _default_fs_write(self, params: dict) -> dict:
        raw_path = params.get("path", "")
        content = params.get("content", "")
        p = Path(raw_path).resolve()

        # Content size cap before any I/O.
        if len(content.encode("utf-8")) > _MAX_FS_BYTES:
            raise RuntimeError(
                f"fs/write_text_file denied: content exceeds {_MAX_FS_BYTES} byte limit"
            )

        # Sandbox check: resolved path must be inside project_dir when one is set.
        if self._project_dir is not None:
            project_resolved = self._project_dir.resolve()
            try:
                p.relative_to(project_resolved)
            except ValueError:
                raise RuntimeError(
                    f"fs/write_text_file denied: path {p} is outside project_dir "
                    f"{project_resolved}"
                )

        # Permission gate: must be explicitly pre-approved in the store.
        # We use is_allowed() directly rather than tool_action() because
        # tool_action() defaults to "allow" for unknown tool names — which is
        # unsafe for ACP filesystem access.  Only explicit session/project/global
        # grants in the PermissionStore may authorise a write.
        if self._permission_store is not None:
            if not self._permission_store.is_allowed("acp__fs_write_text_file"):
                raise RuntimeError(
                    "fs/write_text_file denied: no explicit grant in permission store"
                )

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.info("ACP fs/write_text_file: wrote %d bytes to %s", len(content), p)
        return {}

    # ── preserved methods ──

    async def authenticate(self, method_id: str) -> None:
        await self.send_request("session/authenticate", {"methodId": method_id})

    def _inject_env(self, credential_provider=None) -> dict:
        env = os.environ.copy()
        if credential_provider and self._config.credentials_ref:
            try:
                val = credential_provider.get(self._config.credentials_ref)
                env[self._config.credentials_ref] = val
            except KeyError:
                logger.warning("Credential %s not found for agent %s", self._config.credentials_ref, self._config.name)

        if self._config.model_override:
            agent_name = self._config.name
            model_override = self._config.model_override

            if agent_name.startswith("claude-code"):
                env["ANTHROPIC_MODEL"] = model_override

            elif agent_name.startswith("goose"):
                if "/" in model_override:
                    provider, model = model_override.split("/", 1)
                    env["GOOSE_PROVIDER"] = provider
                    env["GOOSE_MODEL"] = model
                else:
                    env["GOOSE_MODEL"] = model_override

            elif agent_name.startswith("codex"):
                pass

        if self._config.thinking_budget > 0 and self._config.name == "claude-code":
            env["MAX_THINKING_TOKENS"] = str(self._config.thinking_budget)

        return env
