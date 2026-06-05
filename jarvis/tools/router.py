from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


GATE_TOOLS = {"powershell", "write_file", "create_file"}


class UnknownToolError(Exception):
    pass


@dataclass
class ToolResult:
    status: str  # success | error
    output: str
    duration_ms: int = 0


class ToolRouter:
    def __init__(
        self,
        shell: str,
        wsl_distro: str,
        tool_output_max_tokens: int,
        brave_api_key: str | None,
    ) -> None:
        self._shell = shell
        self._wsl_distro = wsl_distro
        self._max_tokens = tool_output_max_tokens
        self._brave_key = brave_api_key
        self._session_auto_approve: set[str] = set()
        self._registry = self._build_registry()

    def _build_registry(self) -> dict[str, Callable]:
        from jarvis.tools.files import read_file, write_file, create_file, list_dir
        from jarvis.tools.search import search_files
        from jarvis.tools.web import fetch_url

        reg: dict[str, Callable] = {
            "read_file": read_file,
            "write_file": write_file,
            "create_file": create_file,
            "list_dir": list_dir,
            "search_files": search_files,
            "fetch_url": fetch_url,
        }

        from jarvis.tools.powershell import run_powershell
        reg["powershell"] = run_powershell

        if self._brave_key:
            from jarvis.tools.web import web_search
            reg["web_search"] = web_search

        return reg

    def tool_names(self) -> list[str]:
        return list(self._registry.keys())

    def validate_name(self, name: str) -> None:
        if name not in self._registry:
            raise UnknownToolError(f"Unknown tool: {name!r}. Valid tools: {self.tool_names()}")

    def requires_approval(self, name: str) -> bool:
        if name in self._session_auto_approve:
            return False
        return name in GATE_TOOLS

    def set_auto_approved(self, tools: list[str]) -> None:
        self._session_auto_approve.update(tools)

    def execute_sync(self, name: str, args: dict[str, Any]) -> ToolResult:
        import time
        self.validate_name(name)
        fn = self._registry[name]
        start = time.monotonic()
        try:
            if name == "powershell":
                result = fn(args, shell=self._shell, wsl_distro=self._wsl_distro)
            elif name == "web_search":
                result = fn(args, api_key=self._brave_key)
            else:
                result = fn(args)
            duration_ms = int((time.monotonic() - start) * 1000)
            output = self._truncate(result)
            return ToolResult(status="success", output=output, duration_ms=duration_ms)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolResult(status="error", output=str(exc), duration_ms=duration_ms)

    def _truncate(self, text: str) -> str:
        max_chars = self._max_tokens * 4
        if len(text) <= max_chars:
            return text
        token_estimate = len(text) // 4
        return text[:max_chars] + f"\n[...output truncated at {self._max_tokens} tokens — ~{token_estimate} total tokens in result]"

    def anthropic_tool_schemas(self) -> list[dict]:
        schemas = []
        for name in self._registry:
            schemas.append(_TOOL_SCHEMAS[name])
        return schemas


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
        "description": "HTTP GET a URL and return the page content as text. Does not execute JavaScript.",
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
        "description": "Search the web using Brave Search. Returns titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
}
