# ACP Connections — Task Plan
**Generated:** 2026-06-07
**AC coverage:** US-ACP-001 through US-ACP-006
**NFRs in scope:** PERF-001, PERF-002, PERF-003, AVAIL-001, AVAIL-002, SEC-001, SEC-002, SEC-003, MAIN-001, USE-001, USE-002
**Estimated waves:** 5
**Parallelizable tasks:** 0 of 6 (solo dev, sequential)

## Anti-patterns to watch (from learnings.jsonl)
None recorded.

---

## Tasks

### Task 1: Agent Registry — config-backed CRUD for ACP agent definitions

**AC reference:** US-ACP-002 AC-1, AC-2, AC-3
**NFRs in scope:** USE-001, MAIN-001
**Complexity:** S
**Depends on:** none
**File set:** `aede/acp/registry.py`, `tests/test_acp_registry.py`

**Failing test to write first:**
```python
import pytest
from pathlib import Path
from aede.acp.registry import AgentRegistry, AgentConfig, AgentTransport


def test_add_and_list_agents(tmp_path):
    """US-ACP-002 AC-1: Register an agent and verify it appears in the list."""
    registry = AgentRegistry(config_dir=tmp_path)

    registry.add(AgentConfig(
        name="claude-agent",
        transport=AgentTransport.LOCAL,
        command="npx",
        args=["@agentclientprotocol/claude-agent-acp"],
    ))

    agents = registry.list_all()
    assert len(agents) == 1
    assert agents[0].name == "claude-agent"
    assert agents[0].transport == AgentTransport.LOCAL
    assert agents[0].command == "npx"
```

**RED command:** `uv run pytest tests/test_acp_registry.py -x -q`
**Expected RED output:** `ModuleNotFoundError: No module named 'aede.acp'`

**Implementation goal:** Persist and retrieve ACP agent configurations from aede's config system.

**Minimal implementation:**
```python
# aede/acp/__init__.py — empty
# aede/acp/registry.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json


class AgentTransport(Enum):
    LOCAL = "local"


@dataclass
class AgentConfig:
    name: str
    transport: AgentTransport
    command: str
    args: list[str] = field(default_factory=list)
    credentials_ref: Optional[str] = None


class AgentRegistry:
    def __init__(self, config_dir: Path) -> None:
        self._path = config_dir / "agents.json"
        self._agents: dict[str, AgentConfig] = {}
        if self._path.exists():
            self._load()

    def add(self, config: AgentConfig) -> None:
        if config.name in self._agents:
            raise ValueError(f"An agent named '{config.name}' already exists")
        self._agents[config.name] = config
        self._save()

    def get(self, name: str) -> AgentConfig:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found")
        return self._agents[name]

    def remove(self, name: str) -> None:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found")
        del self._agents[name]
        self._save()

    def list_all(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def _save(self) -> None:
        data = {
            name: {
                "transport": a.transport.value,
                "command": a.command,
                "args": a.args,
                "credentials_ref": a.credentials_ref,
            }
            for name, a in self._agents.items()
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        for name, cfg in data.items():
            self._agents[name] = AgentConfig(
                name=name,
                transport=AgentTransport(cfg["transport"]),
                command=cfg["command"],
                args=cfg.get("args", []),
                credentials_ref=cfg.get("credentials_ref"),
            )
```

**GREEN command:** `uv run pytest tests/test_acp_registry.py -x -q`
**Verification step:** `uv run pytest tests/test_acp_registry.py -v`

**Commit:** `feat: Task 1 — Agent Registry (satisfies US-ACP-002 AC-1,2,3)`

---

### Task 2: ACP Client Core — stdio connection and initialize handshake

**AC reference:** US-ACP-001 AC-1, AC-3
**NFRs in scope:** PERF-001, SEC-003
**Complexity:** M
**Depends on:** Task 1
**File set:** `aede/acp/client.py`, `tests/test_acp_client.py`

**Failing test to write first:**
```python
import pytest
from pathlib import Path
from aede.acp.client import AcpClient
from aede.acp.registry import AgentConfig, AgentTransport


def test_connect_to_echo_agent(tmp_path, monkeypatch):
    """US-ACP-001 AC-1: Spawn an echo agent and complete the initialize handshake.

    Uses a small Python script as a fake ACP agent that speaks JSON-RPC 2.0
    over stdio — responds to initialize with protocolVersion 1."""
    echo_script = tmp_path / "echo_agent.py"
    echo_script.write_text("""
import sys, json

def read_msg():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def write_msg(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read_msg()
assert req["method"] == "initialize"
assert req["params"]["protocolVersion"] == 1

write_msg({
    "jsonrpc": "2.0",
    "id": req["id"],
    "result": {
        "protocolVersion": 1,
        "agentCapabilities": {"loadSession": False},
        "agentInfo": {"name": "echo", "title": "Echo Agent", "version": "0.0.0"},
        "authMethods": [],
    },
})
""")

    config = AgentConfig(
        name="echo",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(echo_script)],
    )

    client = AcpClient(config)
    result = client.initialize()

    assert result.protocol_version == 1
    assert result.agent_info.name == "echo"
```

**RED command:** `uv run pytest tests/test_acp_client.py -x -q`
**Expected RED output:** `ModuleNotFoundError: No module named 'aede.acp.client'`

**Implementation goal:** Spawn an ACP agent subprocess, perform the JSON-RPC 2.0 initialize handshake, and return protocol/capability info.

**Minimal implementation:**
```python
# aede/acp/client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import asyncio
import json
import subprocess
import sys
import threading
import queue

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


class AcpClient:
    """ACP client that communicates with an agent subprocess over stdio.

    Uses a dedicated asyncio event loop thread for the async Python SDK
    (per ADR-ACP-001). The public API is synchronous; async work is
    dispatched to the background thread via queues."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._pending: dict[int, queue.Queue] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def initialize(self) -> InitializeResult:
        self._start()
        return self._send_request("initialize", {
            "protocolVersion": ACP_PROTOCOL_VERSION,
            "clientCapabilities": {
                "fs": {"readTextFile": True, "writeTextFile": True},
                "terminal": True,
            },
            "clientInfo": {
                "name": "aede",
                "title": "aede",
                "version": "0.1.0",
            },
        })

    def _start(self) -> None:
        self._process = subprocess.Popen(
            [self._config.command] + self._config.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _send_request(self, method: str, params: dict) -> dict:
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

        line = self._process.stdout.readline()
        response = json.loads(line)
        assert response["id"] == req_id

        if "error" in response:
            raise AcpError(response["error"]["code"], response["error"]["message"])

        result = response["result"]
        if method == "initialize":
            return InitializeResult(
                protocol_version=result["protocolVersion"],
                agent_capabilities=result.get("agentCapabilities", {}),
                agent_info=AgentInfo(**result["agentInfo"]),
                auth_methods=result.get("authMethods", []),
            )
        return result


class AcpError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"ACP error {code}: {message}")
```

**GREEN command:** `uv run pytest tests/test_acp_client.py -x -q`
**Verification step:** `uv run pytest tests/test_acp_client.py tests/test_acp_registry.py -v`

**Commit:** `feat: Task 2 — ACP Client Core (satisfies US-ACP-001 AC-1,3)`

---

### Task 3: Prompt Turn Lifecycle — session/new, session/prompt, streaming updates

**AC reference:** US-ACP-001 AC-1, US-ACP-004 AC-1, AC-2, AC-3
**NFRs in scope:** PERF-002, PERF-003, AVAIL-001, SEC-003
**Complexity:** M
**Depends on:** Task 2
**File set:** `aede/acp/client.py`, `aede/acp/session.py`, `aede/acp/stream.py`, `tests/test_acp_session.py`

**Failing test to write first:**
```python
import pytest
from pathlib import Path
from aede.acp.client import AcpClient
from aede.acp.session import AcpSession
from aede.acp.registry import AgentConfig, AgentTransport


def test_session_create_and_prompt(tmp_path):
    """US-ACP-001 AC-1 + US-ACP-004 AC-1: Create a session and receive streamed updates."""
    # Fake agent that responds to session/new and session/prompt
    agent_script = tmp_path / "fake_agent.py"
    agent_script.write_text("""
import sys, json

def read():
    return json.loads(sys.stdin.readline())

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

# initialize
req = read()
write({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentCapabilities":{},"agentInfo":{"name":"fake","title":"Fake","version":"0"},"authMethods":[]}})

# session/new
req = read()
assert req["method"] == "session/new"
write({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"sess_001"}})

# session/prompt
req = read()
assert req["method"] == "session/prompt"

# stream an update before responding
write({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"sess_001","update":{"sessionUpdate":"agent_message_chunk","messageId":"msg_1","content":{"type":"text","text":"Hello from fake agent"}}}})

# respond to session/prompt
write({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}})
""")

    config = AgentConfig(
        name="fake",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(agent_script)],
    )

    client = AcpClient(config)
    client.initialize()

    session = AcpSession(client)
    session_id = session.create(cwd=str(tmp_path))

    updates = []
    result = session.prompt("Hello", on_update=lambda u: updates.append(u))

    assert session_id == "sess_001"
    assert result.stop_reason == "end_turn"
    assert len(updates) == 1
    assert updates[0]["sessionUpdate"] == "agent_message_chunk"
    assert updates[0]["content"]["text"] == "Hello from fake agent"
```

**RED command:** `uv run pytest tests/test_acp_session.py -x -q`
**Expected RED output:** `ModuleNotFoundError: No module named 'aede.acp.session'`

**Implementation goal:** Extend AcpClient with session/new, session/prompt methods. Add AcpSession that manages the turn lifecycle and routes session/update notifications through a callback.

**GREEN command:** `uv run pytest tests/test_acp_session.py -x -q`
**Verification step:** `uv run pytest tests/test_acp_client.py tests/test_acp_session.py tests/test_acp_registry.py -v`

**Commit:** `feat: Task 3 — Prompt Turn Lifecycle (satisfies US-ACP-001 AC-1, US-ACP-004 AC-1,2,3)`

---

### Task 4: Permission Bridge — ACP request_permission → aede gate

**AC reference:** US-ACP-003 AC-1, AC-2, AC-3, AC-4
**NFRs in scope:** NFR-SEC-002
**Complexity:** S
**Depends on:** Task 3
**File set:** `aede/acp/permissions.py`, `tests/test_acp_permissions.py`

**Failing test to write first:**
```python
import pytest
from aede.acp.permissions import AcpPermissionBridge, AcpPermissionOutcome
from aede.gate import PermissionStore


def test_allow_once_maps_to_gate(tmp_path):
    """US-ACP-003 AC-1: allow_once ACP option maps to aede gate allow_once."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="call_001",
        options=[
            {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
            {"optionId": "reject-once", "name": "Reject", "kind": "reject_once"},
        ],
        choice="allow-once",
    )

    assert result.outcome == AcpPermissionOutcome.ALLOWED
    assert result.option_id == "allow-once"


def test_deny_maps_to_gate(tmp_path):
    """US-ACP-003 AC-3: reject_once ACP option maps to aede gate deny."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="call_002",
        options=[
            {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
            {"optionId": "reject-once", "name": "Reject", "kind": "reject_once"},
        ],
        choice="reject-once",
    )

    assert result.outcome == AcpPermissionOutcome.DENIED


def test_always_allow_persists_to_store(tmp_path):
    """US-ACP-003 AC-2: always_allow maps to aede gate session-level allow."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="call_003",
        options=[
            {"optionId": "allow-always", "name": "Always allow", "kind": "allow_always"},
            {"optionId": "reject-once", "name": "Reject", "kind": "reject_once"},
        ],
        choice="allow-always",
    )

    assert result.outcome == AcpPermissionOutcome.ALLOWED
    assert store.is_allowed("acp__call_003") is True


def test_cancelled_prompt_rejects_all():
    """US-ACP-003 AC-4: Cancelled prompt returns cancelled outcome."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve_cancelled("call_004")
    assert result.outcome == AcpPermissionOutcome.CANCELLED
```

**RED command:** `uv run pytest tests/test_acp_permissions.py -x -q`
**Expected RED output:** `ModuleNotFoundError: No module named 'aede.acp.permissions'`

**Implementation goal:** Map ACP `session/request_permission` options to aede's `PermissionStore` decisions. Convert aede gate outcomes back to ACP-compatible JSON-RPC responses. Handle cancellation.

**GREEN command:** `uv run pytest tests/test_acp_permissions.py -x -q`
**Verification step:** `uv run pytest tests/test_acp_permissions.py tests/test_acp_session.py -v`

**Commit:** `feat: Task 4 — Permission Bridge (satisfies US-ACP-003 AC-1,2,3,4)`

---

### Task 5: Credential Provider — vault passthrough for ACP agent auth

**AC reference:** US-ACP-006 AC-1
**NFRs in scope:** SEC-001
**Complexity:** S
**Depends on:** Task 1
**File set:** `aede/acp/credentials.py`, `tests/test_acp_credentials.py`

**Failing test to write first:**
```python
import json
import pytest
from pathlib import Path
from aede.acp.credentials import CredentialProvider
from aede.acp.registry import AgentConfig, AgentTransport


def test_get_credential_from_vault(tmp_path):
    """US-ACP-006 AC-1: Retrieve a credential from the vault by reference."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"CLAUDE_API_KEY": "sk-ant-abc123"}))

    provider = CredentialProvider(vault_dir=tmp_path)
    key = provider.get("CLAUDE_API_KEY")

    assert key == "sk-ant-abc123"


def test_missing_credential_raises(tmp_path):
    """US-ACP-006 AC-1 edge case: missing credential produces clear error."""
    provider = CredentialProvider(vault_dir=tmp_path)

    with pytest.raises(KeyError, match="Credential 'MISSING_KEY' not found"):
        provider.get("MISSING_KEY")


def test_credential_not_logged(capsys, tmp_path):
    """SEC-001: Credential values must not appear in stdout/logs."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"SECRET": "sk-secret-xyz"}))

    provider = CredentialProvider(vault_dir=tmp_path)
    _key = provider.get("SECRET")

    captured = capsys.readouterr()
    assert "sk-secret-xyz" not in captured.out
    assert "sk-secret-xyz" not in captured.err


def test_provider_with_agent_config_field(tmp_path):
    """US-ACP-006 AC-1: Credential provider resolves credentials_ref from AgentConfig."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"GEMINI_API_KEY": "gemini-key-456"}))

    config = AgentConfig(
        name="gemini",
        transport=AgentTransport.LOCAL,
        command="gemini",
        args=["--experimental-acp"],
        credentials_ref="GEMINI_API_KEY",
    )

    provider = CredentialProvider(vault_dir=tmp_path)
    key = provider.get_for_agent(config)

    assert key == "gemini-key-456"
```

**RED command:** `uv run pytest tests/test_acp_credentials.py -x -q`
**Expected RED output:** `ModuleNotFoundError: No module named 'aede.acp.credentials'`

**Implementation goal:** Read credentials from aede's existing vault (`~/.aede/credentials.json`) by key name reference. Support the `credentials_ref` field on AgentConfig. Never log credential values. Raise clear errors for missing credentials.

**GREEN command:** `uv run pytest tests/test_acp_credentials.py -x -q`
**Verification step:** `uv run pytest tests/test_acp_credentials.py -v`

**Commit:** `feat: Task 5 — Credential Provider (satisfies US-ACP-006 AC-1, SEC-001)`

---

### Task 6: Multi-Agent Session Manager — agent switching with session isolation

**AC reference:** US-ACP-005 AC-1, US-ACP-001 AC-2, NFR-AVAIL-002
**NFRs in scope:** AVAIL-001, AVAIL-002, USE-002
**Complexity:** M
**Depends on:** Task 2, Task 3, Task 4, Task 5
**File set:** `aede/acp/manager.py`, `tests/test_acp_manager.py`

**Failing test to write first:**
```python
import json
import pytest
from pathlib import Path
from aede.acp.manager import AcpManager
from aede.acp.registry import AgentRegistry, AgentConfig, AgentTransport
from aede.acp.credentials import CredentialProvider


@pytest.fixture
def agent_script_factory(tmp_path):
    """Create a fake ACP agent script that responds to initialize + session/new."""
    def _make(name: str) -> Path:
        script = tmp_path / f"{name}_agent.py"
        script.write_text(f'''
import sys, json
def read(): return json.loads(sys.stdin.readline())
def write(m): sys.stdout.write(json.dumps(m)+"\\n"); sys.stdout.flush()

req = read()
write({{"jsonrpc":"2.0","id":req["id"],"result":{{"protocolVersion":1,"agentCapabilities":{{}},"agentInfo":{{"name":"{name}","title":"{name}","version":"0"}},"authMethods":[]}}}})

req = read()
write({{"jsonrpc":"2.0","id":req["id"],"result":{{"sessionId":"sess_{name}"}}}})
''')
        return script
    return _make


def test_switch_between_agents(tmp_path, agent_script_factory):
    """US-ACP-005 AC-1: Connect to two agents and switch between them."""
    agent_a = agent_script_factory("alpha")
    agent_b = agent_script_factory("beta")

    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(name="alpha", transport=AgentTransport.LOCAL, command="python", args=[str(agent_a)]))
    registry.add(AgentConfig(name="beta", transport=AgentTransport.LOCAL, command="python", args=[str(agent_b)]))

    manager = AcpManager(registry, CredentialProvider(vault_dir=tmp_path))

    # Connect to alpha
    sid_a = manager.connect("alpha")
    assert sid_a == "sess_alpha"

    # Switch to beta (alpha session preserved)
    sid_b = manager.connect("beta")
    assert sid_b == "sess_beta"

    # Active session is beta
    assert manager.active_session_id() == "sess_beta"

    # Switch back to alpha
    manager.switch_to("alpha")
    assert manager.active_session_id() == "sess_alpha"


def test_agent_not_found_error(agent_script_factory, tmp_path):
    """US-ACP-001 AC-2 + USE-002: Clear error when agent binary not found."""
    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(
        name="missing",
        transport=AgentTransport.LOCAL,
        command="nonexistent-binary-xyz",
        args=[],
    ))

    manager = AcpManager(registry, CredentialProvider(vault_dir=tmp_path))

    with pytest.raises(FileNotFoundError, match="Agent 'missing' not found"):
        manager.connect("missing")


def test_agent_crash_isolated(agent_script_factory, tmp_path):
    """AVAIL-002: Crash of one agent subprocess does not crash aede or affect other sessions."""
    # Create a stable agent
    stable = agent_script_factory("stable")

    # Create a crashing agent (exits before responding)
    crash_script = tmp_path / "crash_agent.py"
    crash_script.write_text("import sys; sys.exit(1)")

    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(name="stable", transport=AgentTransport.LOCAL, command="python", args=[str(stable)]))
    registry.add(AgentConfig(name="crash", transport=AgentTransport.LOCAL, command="python", args=[str(crash_script)]))

    manager = AcpManager(registry, CredentialProvider(vault_dir=tmp_path))

    # Connect stable first
    sid_stable = manager.connect("stable")
    assert sid_stable is not None

    # Attempt to connect to crashing agent
    with pytest.raises(Exception):
        manager.connect("crash")

    # Stable session still works
    assert manager.active_session_id() == sid_stable
```

**RED command:** `uv run pytest tests/test_acp_manager.py -x -q`
**Expected RED output:** `ModuleNotFoundError: No module named 'aede.acp.manager'`

**Implementation goal:** Orchestrate multiple ACP agent connections. Track which agent is active. Switch between agents without closing inactive sessions. Handle agent crashes without affecting other sessions. Map errors to clear user-facing messages.

**GREEN command:** `uv run pytest tests/test_acp_manager.py -x -q`
**Verification step:** `uv run pytest tests/test_acp_manager.py tests/test_acp_session.py tests/test_acp_permissions.py tests/test_acp_credentials.py -v`

**Commit:** `feat: Task 6 — Multi-Agent Session Manager (satisfies US-ACP-005 AC-1, US-ACP-001 AC-2, AVAIL-001, AVAIL-002, USE-002)`

---

## Dependency graph

```
Wave 0: Task 1 (Agent Registry)
Wave 1: Task 2 (ACP Client Core) ← depends on Task 1
         Task 5 (Credential Provider) ← depends on Task 1
Wave 2: Task 3 (Prompt Turn Lifecycle) ← depends on Task 2
Wave 3: Task 4 (Permission Bridge) ← depends on Task 3
Wave 4: Task 6 (Multi-Agent Session Manager) ← depends on Task 2,3,4,5
```

**Critical path:** Task 1 → Task 2 → Task 3 → Task 4 → Task 6

**Parallelization:** Not applicable (solo dev). All tasks are sequential on the critical path. Task 5 could run in parallel with Task 2 (disjoint file sets, no dependency between them), but solo dev means sequential anyway.

---

## AC coverage matrix

| Story | ACs | Task |
|---|---|---|
| US-ACP-001 AC-1 (connect, initialize, create session) | 1 scenario | Task 2, Task 3 |
| US-ACP-001 AC-2 (agent not found error) | 1 scenario | Task 6 |
| US-ACP-001 AC-3 (agent returns error) | 1 scenario | Task 2 |
| US-ACP-002 AC-1 (add agent) | 1 scenario | Task 1 |
| US-ACP-002 AC-2 (duplicate name) | 1 scenario | Task 1 |
| US-ACP-002 AC-3 (missing transport) | 1 scenario | Task 1 |
| US-ACP-003 AC-1 (allow once) | 1 scenario | Task 4 |
| US-ACP-003 AC-2 (always allow) | 1 scenario | Task 4 |
| US-ACP-003 AC-3 (deny) | 1 scenario | Task 4 |
| US-ACP-003 AC-4 (cancelled) | 1 scenario | Task 4 |
| US-ACP-004 AC-1 (text streaming) | 1 scenario | Task 3 |
| US-ACP-004 AC-2 (tool call updates) | 1 scenario | Task 3 |
| US-ACP-004 AC-3 (empty response) | 1 scenario | Task 3 |
| US-ACP-005 AC-1 (switch agents) | 1 scenario | Task 6 |
| US-ACP-006 AC-1 (connect with stored credentials) | 1 scenario | Task 5 |

**Deferred (Could-have):** US-ACP-007 (remote agents — blocked on ACP transport RFD), US-ACP-008 (capability discovery UI)

---

## Verification gates

After each wave completes, run the full test suite to confirm no regressions:

```
uv run pytest -x -q
```

Before merging to main:
```
uv run pytest -v
uv run ruff check aede/acp/
```
