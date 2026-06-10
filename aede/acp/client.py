from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional
import json
import os
import shutil
import subprocess
import sys

from .registry import AgentConfig

ACP_PROTOCOL_VERSION = 1


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


class AcpClient:
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0

    def initialize(self, credential_provider=None) -> InitializeResult:
        self._start(credential_provider=credential_provider)
        result = self._send_request("initialize", {
            "protocolVersion": ACP_PROTOCOL_VERSION,
            "clientCapabilities": {
                "fs": {"readTextFile": True, "writeTextFile": True},
                "terminal": True,
                "auth": {"terminal": True},
            },
            "clientInfo": {
                "name": "aede",
                "title": "aede",
                "version": "0.1.0",
            },
        }, timeout=120.0)
        if result.protocol_version != ACP_PROTOCOL_VERSION:
            raise ValueError(
                f"Unsupported protocol version {result.protocol_version}: "
                f"aede supports v{ACP_PROTOCOL_VERSION}"
            )
        return result

    def new_session(
        self,
        cwd: str = "",
        mcp_servers: Optional[list] = None,
    ) -> str:
        if mcp_servers is None:
            mcp_servers = []
        result = self._send_request("session/new", {
            "cwd": cwd,
            "mcpServers": mcp_servers,
        })
        return result["sessionId"]

    def prompt(
        self,
        session_id: str,
        text: str,
        message_id: str = "msg_1",
        on_update: Optional[callable] = None,
    ) -> dict:
        req_id = self._request_id
        self._request_id += 1
        msg = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "session/prompt",
            "params": {
                "sessionId": session_id,
                "messageId": message_id,
                "prompt": [{"type": "text", "text": text}],
            },
        })
        assert self._process and self._process.stdin
        self._process.stdin.write(msg + "\n")
        self._process.stdin.flush()

        accumulated_text = ""

        while True:
            line = self._process.stdout.readline()
            if not line:
                raise AcpError(-1, "Agent closed connection")
            response = json.loads(line)

            if "id" in response and response["id"] == req_id:
                if "error" in response:
                    raise AcpError(
                        response["error"]["code"],
                        response["error"]["message"],
                    )
                result = response["result"]
                result["text"] = accumulated_text
                return result

            if response.get("method") == "session/update":
                update = response.get("params", {}).get("update", {})
                if update.get("sessionUpdate") == "agent_message_chunk":
                    content = update.get("content", {})
                    if isinstance(content, dict) and content.get("type") == "text":
                        accumulated_text += content.get("text", "")
                if on_update:
                    on_update(update)

    def authenticate(self, method_id: str) -> None:
        self._send_request("session/authenticate", {"methodId": method_id})

    def close(self) -> None:
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)

    def _inject_env(self, credential_provider=None) -> dict:
        env = os.environ.copy()
        if credential_provider and self._config.credentials_ref:
            try:
                val = credential_provider.get(self._config.credentials_ref)
                env[self._config.credentials_ref] = val
            except KeyError:
                pass
        
        # Inject model override environment variables based on agent type
        if self._config.model_override:
            agent_name = self._config.name
            model_override = self._config.model_override
            
            # Claude Code: ANTHROPIC_MODEL env var
            if agent_name.startswith("claude-code"):
                env["ANTHROPIC_MODEL"] = model_override
            
            # Goose: GOOSE_PROVIDER + GOOSE_MODEL env vars
            elif agent_name.startswith("goose"):
                # Model override format: "provider/model" (e.g., "anthropic/claude-sonnet-4-6")
                if "/" in model_override:
                    provider, model = model_override.split("/", 1)
                    env["GOOSE_PROVIDER"] = provider
                    env["GOOSE_MODEL"] = model
                else:
                    env["GOOSE_MODEL"] = model_override
            
            # Codex: Add --model flag to args (handled in _start)
            elif agent_name.startswith("codex"):
                pass  # Handled in _start method
        
        return env

    def _start(self, credential_provider=None) -> None:
        # Build command with model override flag for Codex
        cmd = [self._config.command] + self._config.args
        if self._config.model_override and self._config.name == "codex":
            cmd.extend(["--model", self._config.model_override])
        
        # Windows: .cmd/.bat files can't be spawned directly by CreateProcess.
        # Resolve via shutil.which and wrap in cmd.exe /c if needed.
        if sys.platform == 'win32':
            resolved = shutil.which(cmd[0])
            if resolved and resolved.lower().endswith(('.cmd', '.bat')):
                cmd = ['cmd.exe', '/c'] + cmd

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._inject_env(credential_provider),
        )

    def _send_request(self, method: str, params: dict, timeout: float = 10.0) -> Any:
        import threading
        req_id = self._request_id
        self._request_id += 1
        msg = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        })
        assert self._process and self._process.stdin
        self._process.stdin.write(msg + "\n")
        self._process.stdin.flush()

        box: dict[str, Any] = {}
        def _read():
            box["line"] = self._process.stdout.readline()
        t = threading.Thread(target=_read, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            raise AcpError(-1, f"Agent '{self._config.name}' timed out after {timeout}s")

        line = box["line"]
        if not line:
            raise AcpError(-1, f"Agent '{self._config.name}' closed connection before responding")
        response = json.loads(line)
        assert response["id"] == req_id

        if "error" in response:
            raise AcpError(
                response["error"]["code"],
                response["error"]["message"],
            )

        result = response["result"]
        if method == "initialize":
            return InitializeResult(
                protocol_version=result["protocolVersion"],
                agent_capabilities=result.get("agentCapabilities", {}),
                agent_info=AgentInfo(**result["agentInfo"]),
                auth_methods=result.get("authMethods", []),
            )
        return result
