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
        data_dir: "Path | None" = None,
    ) -> None:
        self._shell = shell
        self._wsl_distro = wsl_distro
        self._max_tokens = tool_output_max_tokens
        self._db = db
        self._data_dir = data_dir
        self._session_auto_approve: set[str] = set()
        self._registry = self._build_registry()

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
        # Bind db via closure so execute_sync can call it like any other tool.
        _db = self._db
        reg["session_search"] = lambda args: session_search(args, db=_db)

        # write_learning is gated (in GATE_TOOLS) — requires user approval.
        # Bind the LearningsStore via closure; if data_dir is not provided the
        # tool returns an error result rather than raising.
        _data_dir = self._data_dir
        reg["write_learning"] = lambda args: _write_learning_tool(args, data_dir=_data_dir)

        return reg

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
        """
        if name in self._session_auto_approve:
            return False
        return name in GATE_TOOLS

    def set_auto_approved(self, tools: list[str]) -> None:
        """Mark a set of tools as pre-approved for the session (no gate prompt)."""
        self._session_auto_approve.update(tools)

    def execute_sync(self, name: str, args: dict[str, Any]) -> ToolResult:
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
                result = fn(args, shell=self._shell, wsl_distro=self._wsl_distro)
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
    """Tool implementation for write_learning.

    Validates args, writes the learning via LearningsStore, runs the verifier,
    applies the verdict via store.update, and returns a human-readable
    confirmation string.  Verifier errors are caught and logged — they must
    never prevent the write confirmation from being returned.

    Args:
        args: Tool call arguments dict from the agent.
        data_dir: The aede data directory path.  When None, returns an error string.

    Returns:
        A confirmation message string on success.

    Raises:
        ValueError: Propagated from LearningsStore for invalid type/source.
        RuntimeError: When data_dir is not configured.
    """
    if data_dir is None:
        raise RuntimeError(
            "write_learning: no data_dir configured — ToolRouter was constructed without data_dir"
        )

    from pathlib import Path as _Path
    from aede.memory.store import LearningsStore
    from aede.memory.verifier import Verifier  # lazy import

    store = LearningsStore(_Path(data_dir))
    record = store.write_learning(
        type=args["type"],
        content=args["content"],
        source=args["source"],
        source_session_id=args.get("source_session_id", ""),
    )

    # T-11x — post-write verifier hook
    # Code-type learnings use the test-suite path; non-code use LLM coherence.
    # Verification errors are swallowed — never crash the tool.
    try:
        learning_type: str = args["type"]
        verifier = Verifier(
            # Safe defaults for no-API-key / test environments: the injectable
            # deps default to None in Verifier.__init__ — the code path uses
            # _default_test_runner (subprocess) and the LLM path constructs an
            # anthropic.Anthropic() client lazily.  Both are overridable in tests.
        )
        if learning_type in _CODE_LEARNING_TYPES:
            verdict = verifier.run_code_verify(record)
        else:
            verdict = verifier.run_llm_verify(record)

        # Merge verdict into a copy of the record and persist
        updated_record = {**record, **verdict}
        store.update(record["id"], updated_record)
    except Exception:
        # Verification failure — learning is stored but remains unverified.
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
                        "Category of learning. Must be one of: "
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
                        "Origin of the learning. Must be one of: "
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
