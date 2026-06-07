"""
MCP (Model Context Protocol) client for aede.

Manages one or more MCP server subprocesses, each running in its own
background asyncio event loop.  Tools discovered via the MCP handshake
are surfaced to ToolRouter for the LLM to call.
"""
from __future__ import annotations
import asyncio
import concurrent.futures
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MCP_TIMEOUT = 10.0  # seconds per server for spawn
CALL_TIMEOUT = 60.0  # seconds per tool call
SHUTDOWN_GRACE = 5.0  # seconds total for shutdown


@dataclass
class MCPServerConfig:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    trusted: bool = False


def _parse_mcp_servers(raw: dict[str, Any] | None) -> dict[str, MCPServerConfig]:
    """Parse a raw config dict into a dict of MCPServerConfig instances.

    The expected input shape (from YAML) is::

        mcpServers:
          server-name:
            command: npx
            args: [...]
            env: {KEY: val}
            trusted: true
    """
    if not raw:
        return {}
    result: dict[str, MCPServerConfig] = {}
    for name, conf in raw.items():
        if not isinstance(conf, dict):
            continue
        result[name] = MCPServerConfig(
            command=conf.get("command", ""),
            args=conf.get("args", []),
            env=conf.get("env", {}),
            trusted=bool(conf.get("trusted", False)),
        )
    return result


class MCPBridge:
    """Manages MCP server subprocesses and exposes their tools.

    Each MCP server runs in a subprocess managed by the ``mcp`` Python SDK.
    A background daemon thread runs an asyncio event loop that hosts all
    MCP sessions.  Tool calls from the main thread are submitted to the
    bridge loop via ``asyncio.run_coroutine_threadsafe``.
    """

    def __init__(self, servers: dict[str, MCPServerConfig]) -> None:
        self._servers = dict(servers)
        self._sessions: dict[str, Any] = {}
        self._processes: dict[str, Any] = {}
        self._tool_schemas: dict[str, list[dict]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_loop(self) -> None:
        """Entry point for the background thread: create and run the event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    async def _spawn_one(self, name: str, cfg: MCPServerConfig) -> list[dict]:
        """Spawn one MCP server, perform the handshake, and return tool schemas.

        Returns a list of Anthropic-format tool schema dicts (without the
        ``mcp__`` prefix in the name — that is prepended later).
        """
        import mcp
        from mcp.client.stdio import stdio_client

        server_params = mcp.StdioServerParameters(
            command=cfg.command,
            args=cfg.args,
            env={**cfg.env} if cfg.env else None,
        )

        async with stdio_client(server_params) as transport:
            read, write = transport
            async with mcp.ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()

                raw_schemas = []
                for tool in tools_result.tools:
                    raw_schemas.append({
                        "name": tool.name,
                        "description": getattr(tool, "description", "") or "",
                        "input_schema": getattr(tool, "inputSchema", {"type": "object"}),
                    })

                self._sessions[name] = session
                return raw_schemas

    async def spawn_all(self) -> list[str]:
        """Spawn all configured MCP servers concurrently.

        Returns a list of server names that failed to spawn.
        """
        failed: list[str] = []
        tool_schemas: dict[str, list[dict]] = {}

        async def _spawn_with_timeout(name: str, cfg: MCPServerConfig) -> None:
            try:
                schemas = await asyncio.wait_for(
                    self._spawn_one(name, cfg), timeout=MCP_TIMEOUT
                )
                if schemas:
                    tool_schemas[name] = schemas
            except Exception:
                failed.append(name)

        tasks = [_spawn_with_timeout(n, c) for n, c in self._servers.items()]
        if tasks:
            await asyncio.gather(*tasks)

        self._tool_schemas.update(tool_schemas)
        return failed

    def discovered_tools(self) -> list[tuple[str, str, MCPServerConfig, dict]]:
        """Return discovered tools as ``(full_name, server_name, cfg, schema)`` tuples.

        Each tool name is prefixed with ``mcp__<server>__`` to avoid collisions
        with built-in tools.
        """
        result: list[tuple[str, str, MCPServerConfig, dict]] = []
        for server_name, schemas in self._tool_schemas.items():
            cfg = self._servers.get(server_name)
            if cfg is None:
                continue
            for schema in schemas:
                full_name = f"mcp__{server_name}__{schema['name']}"
                anthropic_schema = {
                    "name": full_name,
                    "description": schema.get("description", ""),
                    "input_schema": schema.get("input_schema", {"type": "object"}),
                }
                result.append((full_name, server_name, cfg, anthropic_schema))
        return result

    def call_sync(self, server_name: str, tool_name: str, args: dict) -> str:
        """Call an MCP tool synchronously from the main thread.

        Submits the call to the bridge's event loop and blocks until the
        result is available (up to ``CALL_TIMEOUT`` seconds).
        """
        session = self._sessions.get(server_name)
        if session is None:
            raise RuntimeError(f"MCP server {server_name!r} is not running")

        async def _call() -> str:
            result = await session.call_tool(tool_name, args)
            text_parts: list[str] = []
            for block in getattr(result, "content", []):
                if getattr(block, "type", None) == "text":
                    text_parts.append(getattr(block, "text", ""))
            return "".join(text_parts)

        if self._loop is None:
            raise RuntimeError("Bridge event loop not available")

        future = asyncio.run_coroutine_threadsafe(_call(), self._loop)
        return future.result(timeout=CALL_TIMEOUT)

    def shutdown_all(self) -> None:
        """Close all sessions and kill subprocesses.

        Attempts graceful close first, then force-kills any remaining
        processes after ``SHUTDOWN_GRACE`` seconds total.
        """
        if self._loop is None or self._loop.is_closed():
            return

        async def _close_all() -> None:
            for name, session in list(self._sessions.items()):
                try:
                    await session.__aexit__(None, None, None)
                except Exception:
                    pass
            self._sessions.clear()

        future = asyncio.run_coroutine_threadsafe(_close_all(), self._loop)
        try:
            future.result(timeout=SHUTDOWN_GRACE)
        except Exception:
            pass

        for name, proc in self._processes.items():
            if proc is not None:
                try:
                    p = getattr(proc, "process", proc)
                    if hasattr(p, "poll") and p.poll() is None:
                        p.kill()
                except Exception:
                    pass
        self._processes.clear()

        if self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
