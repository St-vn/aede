import asyncio
import json
import pytest
from pathlib import Path
from aede.acp.permissions import AcpPermissionBridge, AcpPermissionOutcome
from aede.gate import PermissionStore
from aede.acp.client import AcpClient
from aede.acp.registry import AgentConfig, AgentTransport


# ---------------------------------------------------------------------------
# Helpers shared with test_acp_client — duplicated here to keep the test file
# self-contained and avoid test-collection ordering issues.
# ---------------------------------------------------------------------------

class _FakeReader:
    def __init__(self):
        self.q: asyncio.Queue = asyncio.Queue()

    async def readline(self) -> bytes:
        return await self.q.get()

    def feed(self, obj: dict) -> None:
        self.q.put_nowait((json.dumps(obj) + "\n").encode())

    def eof(self) -> None:
        self.q.put_nowait(b"")


class _FakeWriter:
    def __init__(self):
        self.lines: list[bytes] = []

    def write(self, b: bytes) -> None:
        self.lines.append(b)

    async def drain(self) -> None:
        pass


def _wire(client: AcpClient):
    r, w = _FakeReader(), _FakeWriter()
    client._proc = type("P", (), {"stdout": r, "stdin": w, "returncode": None})()
    client._reader_task = asyncio.ensure_future(client._read_loop())
    return r, w


def _last_reply(writer, rid):
    for b in reversed(writer.lines):
        msg = json.loads(b)
        if msg.get("id") == rid:
            return msg
    return None


# ===========================================================================
# Existing AcpPermissionBridge unit tests
# ===========================================================================


def test_allow_once_maps_to_gate():
    """US-ACP-003 AC-1: allow_once → aede gate allow_once."""
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


def test_deny_maps_to_gate():
    """US-ACP-003 AC-3: reject_once → aede gate deny."""
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
    assert result.option_id == "reject-once"


def test_always_allow_persists_to_store():
    """US-ACP-003 AC-2: always_allow → aede gate session-level allow."""
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


def test_cancelled():
    """US-ACP-003 AC-4: Cancelled prompt returns cancelled outcome."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve_cancelled("call_004")

    assert result.outcome == AcpPermissionOutcome.CANCELLED


def test_pre_approved_passes_through():
    """If the tool was already allowed in the store, resolve automatically."""
    store = PermissionStore()
    store.allow_session("acp__read_file")
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="read_file",
        options=[
            {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
        ],
        choice="allow-once",
    )

    assert result.outcome == AcpPermissionOutcome.ALLOWED


# ===========================================================================
# SECURITY: handler-level gate tests (CRITICAL vulnerability fix)
# These tests FAIL on the current ungated code and must PASS after the fix.
# ===========================================================================


# ---------------------------------------------------------------------------
# SEC-1  fs/write_text_file without explicit approval must be denied
# ---------------------------------------------------------------------------

async def test_fs_write_denied_without_approval(tmp_path):
    """SEC-1: fs/write_text_file inbound request with no grant → JSON-RPC error
    and file NOT written on disk.

    Current (vulnerable) code writes unconditionally → RED.
    Fixed code checks PermissionStore → error, file absent → GREEN.
    """
    target = tmp_path / "secret.txt"
    store = PermissionStore(project_dir=tmp_path)
    # NORMAL mode, nothing pre-approved → tool_action returns None (gate required)
    config = AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x")
    client = AcpClient(config, project_dir=tmp_path, permission_store=store)
    r, w = _wire(client)

    r.feed({
        "jsonrpc": "2.0", "id": 20,
        "method": "fs/write_text_file",
        "params": {"path": str(target), "content": "INJECTED"},
    })
    await asyncio.sleep(0.05)

    reply = _last_reply(w, 20)
    assert reply is not None, "handler must reply"
    # Must be a JSON-RPC error, not a success result
    assert "error" in reply, (
        f"expected error (write denied) but got: {reply}"
    )
    # File must NOT have been written
    assert not target.exists(), "file must not be written when permission is denied"

    await client.aclose()


# ---------------------------------------------------------------------------
# SEC-2  fs/read_text_file of a path OUTSIDE project_dir must be denied
# ---------------------------------------------------------------------------

async def test_fs_read_outside_project_dir_denied(tmp_path):
    """SEC-2: fs/read_text_file for a path outside project_dir → error, no read.

    Fixed code resolves the real path and denies anything that escapes project_dir.
    """
    # A file that exists on the filesystem but is outside the project_dir sandbox
    outside_file = tmp_path / "outside" / "credentials.json"
    outside_file.parent.mkdir(parents=True)
    outside_file.write_text('{"secret": "hunter2"}')

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    store = PermissionStore(project_dir=project_dir)
    config = AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x")
    client = AcpClient(config, project_dir=project_dir, permission_store=store)
    r, w = _wire(client)

    r.feed({
        "jsonrpc": "2.0", "id": 21,
        "method": "fs/read_text_file",
        "params": {"path": str(outside_file)},
    })
    await asyncio.sleep(0.05)

    reply = _last_reply(w, 21)
    assert reply is not None, "handler must reply"
    assert "error" in reply, (
        f"expected error (path outside project_dir) but got: {reply}"
    )

    await client.aclose()


# ---------------------------------------------------------------------------
# SEC-3  _default_permission must NOT auto-select "allow" when store denies
# ---------------------------------------------------------------------------

async def test_default_permission_does_not_blindly_allow_when_store_denies():
    """SEC-3: session/request_permission must NOT return an allow optionId when
    the PermissionStore has no grant and mode is NORMAL (gate required).

    Current (vulnerable) code always picks allow_once regardless of the store →
    RED. Fixed code returns cancelled or error → GREEN.
    """
    store = PermissionStore()  # NORMAL mode, nothing pre-approved
    config = AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x")
    client = AcpClient(config, permission_store=store)
    r, w = _wire(client)

    r.feed({
        "jsonrpc": "2.0", "id": 22,
        "method": "session/request_permission",
        "params": {
            "sessionId": "S1",
            "toolCall": {"toolCallId": "tc_bash_001"},
            "options": [
                {"optionId": "opt-allow", "name": "Allow", "kind": "allow_once"},
                {"optionId": "opt-reject", "name": "Reject", "kind": "reject_once"},
            ],
        },
    })
    await asyncio.sleep(0.05)

    reply = _last_reply(w, 22)
    assert reply is not None, "handler must reply"

    # The reply must NOT be outcome=selected with the allow optionId.
    if "result" in reply:
        outcome = reply["result"].get("outcome", {})
        selected_id = outcome.get("optionId", "")
        outcome_value = outcome.get("outcome", "")
        assert not (outcome_value == "selected" and selected_id == "opt-allow"), (
            "_default_permission blindly selected the allow option without "
            "consulting the permission gate — this is the vulnerability"
        )
    # A JSON-RPC error response is also safe (strict deny)

    await client.aclose()


# ---------------------------------------------------------------------------
# SEC-4  fs/write_text_file WITHIN project_dir WITH explicit grant is allowed
# ---------------------------------------------------------------------------

async def test_fs_write_within_project_dir_with_grant_succeeds(tmp_path):
    """SEC-4 (positive): write inside project_dir with session grant → allowed.

    Confirms the fix doesn't over-block legitimate writes that are explicitly
    approved via the permission store.
    """
    target = tmp_path / "output.txt"
    store = PermissionStore(project_dir=tmp_path)
    store.allow_session("acp__fs_write_text_file")  # explicit approval

    config = AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x")
    client = AcpClient(config, project_dir=tmp_path, permission_store=store)
    r, w = _wire(client)

    r.feed({
        "jsonrpc": "2.0", "id": 23,
        "method": "fs/write_text_file",
        "params": {"path": str(target), "content": "hello"},
    })
    await asyncio.sleep(0.05)

    reply = _last_reply(w, 23)
    assert reply is not None
    assert "result" in reply, f"expected success but got: {reply}"
    assert target.exists() and target.read_text() == "hello"

    await client.aclose()


# ---------------------------------------------------------------------------
# SEC-5  Path traversal via ../.. outside project_dir must be denied
# ---------------------------------------------------------------------------

async def test_fs_write_path_traversal_denied(tmp_path):
    """SEC-5: Path traversal (../../etc/passwd style) outside project_dir is denied."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # A path that resolves outside project_dir after normalization
    traversal_target = project_dir / ".." / "escaped.txt"

    store = PermissionStore(project_dir=project_dir)
    config = AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x")
    client = AcpClient(config, project_dir=project_dir, permission_store=store)
    r, w = _wire(client)

    r.feed({
        "jsonrpc": "2.0", "id": 24,
        "method": "fs/write_text_file",
        "params": {"path": str(traversal_target), "content": "ESCAPED"},
    })
    await asyncio.sleep(0.05)

    reply = _last_reply(w, 24)
    assert reply is not None
    assert "error" in reply, (
        f"path traversal outside project_dir must be denied, got: {reply}"
    )
    escaped_file = tmp_path / "escaped.txt"
    assert not escaped_file.exists(), "traversal write must not create file"

    await client.aclose()
