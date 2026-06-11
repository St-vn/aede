"""
Tool registry and dispatcher for the aede agent.

``ToolRouter`` maps tool names to implementation functions, enforces the
approval requirement for gated tools, executes tools synchronously (wrapping
all errors into ``ToolResult`` values so they flow back to the model), and
exposes Anthropic-format JSON schemas for each registered tool.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from pathlib import Path
    from aede.db import DB


GATE_TOOLS = {"powershell", "write_file", "create_file", "write_learning"}


class UnknownToolError(Exception):
    """Raised by ``ToolRouter.validate_name`` when the model requests a non-existent tool."""


class ToolParamError(Exception):
    """Raised by ``ToolRouter.validate_args`` when required params are missing or wrong-typed."""


@dataclass
class ToolResult:
    """Result of a single tool execution returned to the agent loop."""

    status: str  # success | error
    output: str
    duration_ms: int = 0


class ToolRouter:
    """Registry and dispatcher for all agent tools.

    Builds the tool registry at construction time, routes ``execute_sync``
    calls to the correct implementation, truncates oversized outputs, and
    serves Anthropic-format JSON schemas to the provider.
    """

    def __init__(
        self,
        shell: str,
        wsl_distro: str,
        tool_output_max_tokens: int,
        db: "DB | None" = None,
        _cfg: Any = None,
        _gate_store: Any = None,
        _agent_registry: dict[str, Any] | None = None,
        _session_id: str | None = None,
        data_dir: "Path | None" = None,
        _get_bridge: "Callable[[], Any] | None" = None,
    ) -> None:
        self._shell = shell
        self._wsl_distro = wsl_distro
        self._max_tokens = tool_output_max_tokens
        self._db = db
        self._data_dir = data_dir
        self._session_auto_approve: set[str] = set()
        self._cfg = _cfg
        self._gate_store = _gate_store
        self._agent_registry = _agent_registry or {}
        self._session_id = _session_id
        self._registry = self._build_registry()
        self._mcp_bridge: Any = None
        self._trusted_servers: dict[str, bool] = {}
        self._get_bridge = _get_bridge

    def _resolve_bridge(self) -> Any:
        """Return the current MCP bridge, resolving lazily if a getter was provided.

        If ``_get_bridge`` is set (web server flow), it is called on every
        invocation so that bridge restarts are picked up automatically.
        Otherwise falls back to the stored ``_mcp_bridge`` reference (CLI flow).
        """
        if self._get_bridge is not None:
            return self._get_bridge()
        return self._mcp_bridge

    def _build_registry(self) -> dict[str, Callable]:
        from aede.tools.files import read_file, write_file, create_file, list_dir
        from aede.tools.search import search_files
        from aede.tools.web import fetch_url

        reg: dict[str, Callable] = {
            "read_file": read_file,
            "write_file": write_file,
            "create_file": create_file,
            "list_dir": list_dir,
            "search_files": search_files,
            "fetch_url": fetch_url,
        }

        from aede.tools.powershell import run_powershell
        reg["powershell"] = run_powershell

        from aede.tools.web import web_search
        reg["web_search"] = web_search

        from aede.tools.search import session_search
        _db = self._db
        reg["session_search"] = lambda args: session_search(args, db=_db)

        _data_dir = self._data_dir
        reg["write_learning"] = lambda args: _write_learning_tool(args, data_dir=_data_dir)

        if self._cfg is not None and self._gate_store is not None:
            _agent_defs = self._agent_registry
            _o_cfg = self._cfg
            _o_gate = self._gate_store
            _o_sid = self._session_id
            def _spawn(args: dict) -> str:
                agent_name = args.get("agent_name", "")
                task = args.get("task", "")
                agent_def = _agent_defs.get(agent_name)
                if agent_def is None:
                    return f"[error: unknown agent {agent_name!r}]"
                from aede.agents.orchestration import run_subagent
                import asyncio
                coro = run_subagent(
                    agent_def=agent_def,
                    task=task,
                    orchestrator_cfg=_o_cfg,
                    orchestrator_gate_store=_o_gate,
                    orchestrator_session_id=_o_sid,
                    orchestrator_spawn_depth=1,
                )
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop is not None:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                else:
                    return asyncio.run(coro)
            reg["spawn_subagent"] = _spawn
        else:
            reg["spawn_subagent"] = lambda args: "[spawn_subagent: not configured]"

        return reg

    @classmethod
    def from_allowlist(
        cls,
        names: list[str] | None = None,
        disallowed_tools: list[str] | None = None,
        shell: str = "powershell",
        wsl_distro: str = "",
        tool_output_max_tokens: int = 8000,
    ) -> ToolRouter:
        """Construct a ToolRouter with only the named tools registered.

        Args:
            names: List of tool names to include. If None, start with all tools.
            disallowed_tools: List of tool names to exclude (applied after allowlist).
            shell, wsl_distro, tool_output_max_tokens: Passed to constructor.

        Returns:
            New ToolRouter with filtered registry.

        Raises:
            UnknownToolError: If any name in ``names`` is not in the full registry.
        """
        from aede.tools.router import ToolRouter as _TR, UnknownToolError as _UTE

        # Create a temporary router to get the full tool list
        temp = _TR(shell=shell, wsl_distro=wsl_distro, tool_output_max_tokens=tool_output_max_tokens)
        all_tools = temp.tool_names()

        if names is not None:
            for n in names:
                if n not in all_tools:
                    raise _UTE(f"Unknown tool: {n!r}. Valid tools: {all_tools}")

        allowed = list(names) if names is not None else list(all_tools)
        disallowed = set(disallowed_tools or [])
        final_names = [n for n in allowed if n not in disallowed]

        # Build the new router and replace its registry
        router = _TR(shell=shell, wsl_distro=wsl_distro, tool_output_max_tokens=tool_output_max_tokens)
        full_registry = router._registry
        router._registry = {n: full_registry[n] for n in final_names}
        return router

    def register_mcp_tools(
        self,
        discovered: list[tuple[str, str, Any, dict]],
    ) -> None:
        for full_name, server_name, cfg, schema in discovered:
            self._registry[full_name] = self._make_mcp_handler(server_name, full_name)
            _TOOL_SCHEMAS[full_name] = schema
            self._trusted_servers[server_name] = getattr(cfg, "trusted", False)

    def _make_mcp_handler(self, server_name: str, full_name: str) -> Any:
        def handler(args: dict) -> str:
            bridge = self._resolve_bridge()
            if bridge is None:
                return "[error: MCP bridge not initialized]"
            tool_short = full_name.split("__", 2)[2] if "__" in full_name else full_name
            return bridge.call_sync(server_name, tool_short, args)
        return handler

    def tool_names(self) -> list[str]:
        """Return the list of registered tool names."""
        return list(self._registry.keys())

    def validate_name(self, name: str) -> None:
        """Raise ``UnknownToolError`` if ``name`` is not in the registry."""
        if name not in self._registry:
            raise UnknownToolError(f"Unknown tool: {name!r}. Valid tools: {self.tool_names()}")

    def validate_args(self, name: str, args: dict[str, Any]) -> None:
        """Validate ``args`` against the JSON schema for ``name``.

        Raises ``ToolParamError`` when a required field is absent or a field
        has the wrong JSON-schema type (string/integer/number/boolean).
        The schema is read directly from ``_TOOL_SCHEMAS`` — it is the single
        source of truth; no hand-duplicated checks here.

        Heavy import (pydantic) is lazy per project convention.
        """
        schema = _TOOL_SCHEMAS.get(name, {}).get("input_schema", {})
        properties: dict[str, Any] = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        # Check required fields first.
        for field in required:
            if field not in args:
                raise ToolParamError(
                    f"Tool {name!r} missing required field: {field!r}"
                )

        # Type-check fields that are present.
        _JSON_SCHEMA_TO_PYTHON: dict[str, type | tuple] = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
        }
        for field, value in args.items():
            if field not in properties:
                continue  # extra fields are allowed (forward-compat)
            expected_type_str: str = properties[field].get("type", "")
            expected_python = _JSON_SCHEMA_TO_PYTHON.get(expected_type_str)
            if expected_python is None:
                continue  # object/array/unknown — skip type check
            if not isinstance(value, expected_python):
                raise ToolParamError(
                    f"Tool {name!r} field {field!r}: expected {expected_type_str}, "
                    f"got {type(value).__name__!r}"
                )

    def requires_approval(self, name: str) -> bool:
        """Return True if the tool must pass through the user approval gate.

        Session-level auto-approvals bypass the gate.
        MCP tools (mcp__ prefix) check the trusted_servers map.
        """
        if name in self._session_auto_approve:
            return False
        if name.startswith("mcp__"):
            parts = name.split("__", 2)
            if len(parts) >= 2:
                server_name = parts[1]
                return not self._trusted_servers.get(server_name, False)
        return name in GATE_TOOLS

    def set_auto_approved(self, tools: list[str]) -> None:
        """Mark a set of tools as pre-approved for the session (no gate prompt)."""
        self._session_auto_approve.update(tools)

    def execute_sync(self, name: str, args: dict[str, Any], stream_callback: Any = None) -> ToolResult:
        """Dispatch a tool call synchronously and return a ``ToolResult``.

        Any exception raised by the tool implementation is caught and returned
        as a ``ToolResult`` with ``status="error"``; errors are never hidden
        from the model.
        """
        import time
        self.validate_name(name)
        fn = self._registry[name]
        start = time.monotonic()
        try:
            if name == "powershell":
                result = fn(args, shell=self._shell, wsl_distro=self._wsl_distro, stream_callback=stream_callback)
            elif name == "web_search":
                result = fn(args)
            else:
                result = fn(args)
            duration_ms = int((time.monotonic() - start) * 1000)
            output = self._truncate(result)
            return ToolResult(status="success", output=output, duration_ms=duration_ms)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(status="error", output=str(exc), duration_ms=duration_ms)

    def _truncate(self, text: str) -> str:
        """Truncate tool output that exceeds the configured token cap."""
        max_chars = self._max_tokens * 4
        if len(text) <= max_chars:
            return text
        token_estimate = len(text) // 4
        return text[:max_chars] + f"\n[...output truncated at {self._max_tokens} tokens — ~{token_estimate} total tokens in result]"

    def anthropic_tool_schemas(self) -> list[dict]:
        """Return the Anthropic-format tool schema list for all registered tools."""
        schemas = []
        for name in self._registry:
            schemas.append(_TOOL_SCHEMAS[name])
        return schemas


_CODE_LEARNING_TYPES = frozenset({"anti-pattern", "failed-approach"})


def _write_learning_tool(args: dict[str, Any], data_dir: "Path | None") -> str:
    """Tool implementation for write_learning with verifier integration."""
    if data_dir is None:
        raise RuntimeError(
            "write_learning: no data_dir configured — ToolRouter was constructed without data_dir"
        )

    from pathlib import Path as _Path
    from aede.memory.store import LearningsStore
    from aede.memory.verifier import Verifier

    store = LearningsStore(_Path(data_dir))
    record = store.write_learning(
        type=args["type"],
        content=args["content"],
        source=args["source"],
        source_session_id=args.get("source_session_id", ""),
    )

    try:
        learning_type: str = args["type"]
        verifier = Verifier()
        if learning_type in _CODE_LEARNING_TYPES:
            verdict = verifier.run_code_verify(record)
        else:
            verdict = verifier.run_llm_verify(record)
        updated_record = {**record, **verdict}
        store.update(record["id"], updated_record)
    except Exception:
        pass

    return f"Learning written: id={record['id']} type={record['type']!r} source={record['source']!r}"


_TOOL_SCHEMAS: dict[str, dict] = {
    "powershell": {
        "name": "powershell",
        "description": "Execute a PowerShell command. Returns stdout and stderr combined.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "The command to execute."}
            },
            "required": ["cmd"],
        },
    },
    "read_file": {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path."}
            },
            "required": ["path"],
        },
    },
    "write_file": {
        "name": "write_file",
        "description": "Overwrite an existing file with new content. Fails if the file does not exist — use create_file for new files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    "create_file": {
        "name": "create_file",
        "description": "Create a new file with the given content. Fails if the file already exists — use write_file to overwrite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    "list_dir": {
        "name": "list_dir",
        "description": "List directory contents. Returns file names, sizes, and modification times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "depth": {"type": "integer", "default": 1},
            },
            "required": ["path"],
        },
    },
    "search_files": {
        "name": "search_files",
        "description": "Search for a regex pattern across files using ripgrep. Returns matches with file path and line number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern", "path"],
        },
    },
    "fetch_url": {
        "name": "fetch_url",
        "description": "HTTP GET a specific known URL and return the page content as text. Does not execute JavaScript. For HTML pages returns extracted visible text — summarize it, do not quote it back. Use web_search first to find URLs; only use this to fetch a URL you already have.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
            },
            "required": ["url"],
        },
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. No API key required. Returns titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    "spawn_subagent": {
        "name": "spawn_subagent",
        "description": "Spawn a subagent to work on a task independently. Provide the agent_name (must match a loaded agent) and the task description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Name of the agent to spawn."},
                "task": {"type": "string", "description": "Task description for the subagent."},
            },
            "required": ["agent_name", "task"],
        },
    },
    "session_search": {
        "name": "session_search",
        "description": (
            "Search past session message history by keyword using full-text search. "
            "Returns matching messages with ±5 message context window and session bookends."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword or phrase to search for in past messages.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of hit messages to return (default: 10).",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    "write_learning": {
        "name": "write_learning",
        "description": (
            "Persist a learning (an insight, anti-pattern, root-cause, or config correction) "
            "to the long-term learnings store.  This is a memory write — it requires user approval."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": (
                        "Category of learning. "
                        "'anti-pattern', 'failed-approach', 'root-cause', 'config-correction'."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Free-text body of the learning.",
                },
                "source": {
                    "type": "string",
                    "description": (
                        "Origin of the learning. "
                        "'user', 'auto_learned', 'test_failure', 'tool_error'."
                    ),
                },
                "source_session_id": {
                    "type": "string",
                    "description": "ID of the session that produced this learning (optional).",
                },
            },
            "required": ["type", "content", "source"],
        },
    },
}
