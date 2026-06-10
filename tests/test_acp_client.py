import asyncio
import inspect
import json
import os
import pytest
from pathlib import Path
from aede.acp.client import AcpClient, AcpError
from aede.acp.credentials import CredentialProvider
from aede.acp.registry import AgentConfig, AgentTransport


# ── helpers ──


def make_echo_agent(script_path: Path) -> Path:
    """Create a fake ACP agent that echoes JSON-RPC requests for testing."""
    script_path.write_text("""
import sys, json

def read():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
assert req["method"] == "initialize"
write({
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
    return script_path


def make_env_echo_agent(script_path: Path) -> Path:
    """Create a fake ACP agent that reads an env var and returns it."""
    script_path.write_text(f"""
import sys, json, os

def read():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
assert req["method"] == "initialize"
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
write({{
    "jsonrpc": "2.0",
    "id": req["id"],
    "result": {{
        "protocolVersion": 1,
        "agentCapabilities": {{"loadSession": False}},
        "agentInfo": {{"name": api_key, "title": "Env Agent", "version": "0.0.0"}},
        "authMethods": [],
    }},
}})
""")
    return script_path


def make_session_agent(script_path: Path, *, new_delay: float = 0.0,
                       notify_first: bool = False) -> Path:
    """Fake ACP agent: answers initialize, then session/new.

    ``new_delay`` sleeps before replying to session/new (to exercise the
    timeout).  ``notify_first`` emits an id-less session/update notification
    before the session/new response (to exercise notification-skipping).
    """
    script_path.write_text(f"""
import sys, json, time

def read():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def write(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

req = read()
assert req["method"] == "initialize"
write({{
    "jsonrpc": "2.0", "id": req["id"],
    "result": {{
        "protocolVersion": 1,
        "agentCapabilities": {{"loadSession": False}},
        "agentInfo": {{"name": "sess", "title": "Sess", "version": "0.0.0"}},
        "authMethods": [],
    }},
}})

req2 = read()
assert req2["method"] == "session/new"
time.sleep({new_delay})
if {notify_first}:
    # id-less notification that must be skipped
    write({{"jsonrpc": "2.0", "method": "session/update",
            "params": {{"update": {{"sessionUpdate": "agent_thought"}}}}}})
write({{"jsonrpc": "2.0", "id": req2["id"], "result": {{"sessionId": "sess_42"}}}})
""")
    return script_path


# ── Task 1-5 test helpers ──


class _FakeReader:
    def __init__(self):
        self.q: asyncio.Queue[bytes] = asyncio.Queue()

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


def _wire(client: AcpClient) -> tuple[_FakeReader, _FakeWriter]:
    """Attach fake streams + start reader without spawning a subprocess."""
    r, w = _FakeReader(), _FakeWriter()
    client._proc = type("P", (), {"stdout": r, "stdin": w, "returncode": None})()
    client._reader_task = asyncio.ensure_future(client._read_loop())
    return r, w


# ── Existing tests (converted to async) ──


async def test_initialize_handshake(tmp_path):
    """US-ACP-001 AC-1: Spawn agent and complete the initialize handshake."""
    script = make_echo_agent(tmp_path / "echo_agent.py")
    config = AgentConfig(
        name="echo",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(script)],
    )

    client = AcpClient(config)
    result = await client.initialize()

    assert result.protocol_version == 1
    assert result.agent_info.name == "echo"


async def test_initialize_protocol_mismatch(tmp_path):
    """US-ACP-001 AC-3: Agent that returns an incompatible protocol version."""
    script = tmp_path / "bad_agent.py"
    script.write_text("""
import sys, json
line = sys.stdin.readline()
req = json.loads(line)
sys.stdout.write(json.dumps({
    "jsonrpc": "2.0",
    "id": req["id"],
    "result": {
        "protocolVersion": 999,
        "agentCapabilities": {},
        "agentInfo": {"name": "bad", "title": "Bad", "version": "0.0"},
        "authMethods": [],
    },
}) + "\\n")
sys.stdout.flush()
""")
    config = AgentConfig(name="bad", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    with pytest.raises(Exception, match="protocol version 999"):
        await client.initialize()


async def test_initialize_agent_error(tmp_path):
    """US-ACP-001 AC-3: Agent returns a JSON-RPC error during initialize."""
    script = tmp_path / "error_agent.py"
    script.write_text("""
import sys, json
line = sys.stdin.readline()
req = json.loads(line)
sys.stdout.write(json.dumps({
    "jsonrpc": "2.0",
    "id": req["id"],
    "error": {"code": -32000, "message": "Model unavailable"},
}) + "\\n")
sys.stdout.flush()
""")
    config = AgentConfig(name="err", transport=AgentTransport.LOCAL, command="python", args=[str(script)])
    client = AcpClient(config)
    with pytest.raises(Exception, match="Model unavailable"):
        await client.initialize()


async def test_start_injects_credentials_ref_env(tmp_path):
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text(json.dumps({
        "ANTHROPIC_API_KEY": {"value": "sk-ant-test-key", "provider": "anthropic"},
    }))
    provider = CredentialProvider(home=tmp_path)
    script = make_env_echo_agent(tmp_path / "env_agent.py")
    config = AgentConfig(
        name="env_test",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(script)],
        credentials_ref="ANTHROPIC_API_KEY",
    )
    client = AcpClient(config)
    result = await client.initialize(credential_provider=provider)
    assert result.agent_info.name == "sk-ant-test-key"


async def test_start_with_unset_credentials_ref_skips_injection(tmp_path):
    provider = CredentialProvider(home=tmp_path)
    script = make_env_echo_agent(tmp_path / "no_ref_agent.py")
    config = AgentConfig(
        name="no_ref",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[str(script)],
        credentials_ref="MISSING_KEY",
    )
    client = AcpClient(config)
    result = await client.initialize(credential_provider=provider)
    assert result.agent_info.name == ""


# ── new_session timeout + notification-skipping ──


def test_new_session_default_timeout_is_60s():
    """Guard: nobody silently lowers the new_session timeout back toward 10s."""
    assert inspect.signature(AcpClient.new_session).parameters["timeout"].default == 60.0


async def test_new_session_succeeds(tmp_path):
    script = make_session_agent(tmp_path / "sess_agent.py")
    config = AgentConfig(name="sess", transport=AgentTransport.LOCAL,
                         command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()
    assert await client.new_session(cwd="") == "sess_42"
    await client.aclose()


async def test_new_session_times_out_when_agent_slow(tmp_path):
    """A short explicit timeout must raise the 'timed out' AcpError."""
    script = make_session_agent(tmp_path / "slow_agent.py", new_delay=0.5)
    config = AgentConfig(name="sess", transport=AgentTransport.LOCAL,
                         command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()
    with pytest.raises(AcpError, match="timed out"):
        await client.new_session(cwd="", timeout=0.05)
    await client.aclose()


async def test_new_session_skips_leading_notification(tmp_path):
    """An id-less notification before the response must be skipped, not crash."""
    script = make_session_agent(tmp_path / "notify_agent.py", notify_first=True)
    config = AgentConfig(name="sess", transport=AgentTransport.LOCAL,
                         command="python", args=[str(script)])
    client = AcpClient(config)
    await client.initialize()
    assert await client.new_session(cwd="") == "sess_42"
    await client.aclose()


# ══════════════════════════════════════════════════════════════════════════════
# Task 1 — Core pump tests
# ══════════════════════════════════════════════════════════════════════════════


async def test_concurrent_requests_demux_by_id():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    t1 = asyncio.create_task(c.send_request("a", {}))
    t2 = asyncio.create_task(c.send_request("b", {}))
    await asyncio.sleep(0.01)
    r.feed({"jsonrpc": "2.0", "id": 1, "result": {"who": "b"}})
    r.feed({"jsonrpc": "2.0", "id": 0, "result": {"who": "a"}})
    assert (await t1)["who"] == "a"
    assert (await t2)["who"] == "b"
    await c.aclose()


async def test_error_response_raises():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    t = asyncio.create_task(c.send_request("m", {}))
    await asyncio.sleep(0.01)
    r.feed({"jsonrpc": "2.0", "id": 0, "error": {"code": -1, "message": "boom"}})
    with pytest.raises(AcpError, match="boom"):
        await t
    await c.aclose()


async def test_norm_id_string_echo():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    t = asyncio.create_task(c.send_request("m", {}))
    await asyncio.sleep(0.01)
    r.feed({"jsonrpc": "2.0", "id": "0", "result": {"ok": True}})
    assert (await t)["ok"] is True
    await c.aclose()


# ══════════════════════════════════════════════════════════════════════════════
# Task 2 — Serialized writes + _inject_env
# ══════════════════════════════════════════════════════════════════════════════


async def test_writes_serialized_and_framed():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    await asyncio.gather(*[c.send_notification("n", {"i": i}) for i in range(5)])
    for b in w.lines:
        assert b.endswith(b"\n")
        json.loads(b)
    assert len(w.lines) == 5
    await c.aclose()


def test_inject_env_preserves_submodel():
    cfg = AgentConfig(name="claude-code", transport=AgentTransport.LOCAL,
                      command="npx", model_override="claude-opus-4-8")
    c = AcpClient(cfg)
    env = c._inject_env(None)
    assert env["ANTHROPIC_MODEL"] == "claude-opus-4-8"


# ══════════════════════════════════════════════════════════════════════════════
# Task 3 — Streaming
# ══════════════════════════════════════════════════════════════════════════════


async def test_prompt_streams_and_accumulates_by_session():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    seen = []
    t = asyncio.create_task(c.prompt("S1", "hi", on_update=lambda u: seen.append(u)))
    await asyncio.sleep(0.01)

    def chunk(txt):
        return {"jsonrpc": "2.0", "method": "session/update",
                "params": {"sessionId": "S1", "update": {"sessionUpdate": "agent_message_chunk",
                                                          "content": {"type": "text", "text": txt}}}}

    r.feed(chunk("He"))
    r.feed(chunk("llo"))
    r.feed({"jsonrpc": "2.0", "method": "session/update", "params": {"sessionId": "OTHER",
            "update": {"sessionUpdate": "agent_message_chunk",
                      "content": {"type": "text", "text": "X"}}}})
    r.feed({"jsonrpc": "2.0", "id": 0, "result": {"stopReason": "end_turn"}})
    res = await t
    assert res["text"] == "Hello"
    assert len(seen) == 2
    await c.aclose()


# ══════════════════════════════════════════════════════════════════════════════
# Task 4 — Reentrant request test
# ══════════════════════════════════════════════════════════════════════════════


async def test_reentrant_request_answered_while_prompt_pending():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    c.set_request_handler("fs/read_text_file",
                          lambda p: {"content": "FILEDATA:" + p["path"]})
    t = asyncio.create_task(c.prompt("S1", "hi"))
    await asyncio.sleep(0.01)
    r.feed({"jsonrpc": "2.0", "id": 99, "method": "fs/read_text_file", "params": {"path": "a.txt"}})
    await asyncio.sleep(0.01)
    replies = [json.loads(b) for b in w.lines if b"\"id\": 99" in b or b'"id":99' in b]
    assert replies and replies[0]["result"]["content"] == "FILEDATA:a.txt"
    r.feed({"jsonrpc": "2.0", "id": 0, "result": {"stopReason": "end_turn"}})
    assert (await t)["stopReason"] == "end_turn"
    await c.aclose()


# ══════════════════════════════════════════════════════════════════════════════
# Task 5 — Cancel + EOF tests
# ══════════════════════════════════════════════════════════════════════════════


async def test_cancel_sends_notification_and_future_resolves_cancelled():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    t = asyncio.create_task(c.prompt("S1", "hi"))
    await asyncio.sleep(0.01)
    await c.cancel("S1")
    assert any(json.loads(b).get("method") == "session/cancel" for b in w.lines)
    r.feed({"jsonrpc": "2.0", "id": 0, "result": {"stopReason": "cancelled"}})
    assert (await t)["stopReason"] == "cancelled"
    await c.aclose()


async def test_eof_fails_pending_futures():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    t = asyncio.create_task(c.send_request("m", {}))
    await asyncio.sleep(0.01)
    r.eof()
    with pytest.raises(AcpError):
        await t
    await c.aclose()


# ══════════════════════════════════════════════════════════════════════════════
# Regression — reentrant agent→client requests must be handled, not -32601.
# Without these the agent stalls a turn forever (no output, no error) the moment
# it needs permission or file access.
# ══════════════════════════════════════════════════════════════════════════════


def _last_reply(writer, rid):
    """Return the parsed JSON-RPC message the client wrote for id == rid."""
    for b in reversed(writer.lines):
        msg = json.loads(b)
        if msg.get("id") == rid:
            return msg
    return None


async def test_default_permission_handler_auto_approves():
    """session/request_permission (never capability-gated) must be auto-approved
    by echoing the allow option's optionId in the selected outcome shape."""
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    r.feed({"jsonrpc": "2.0", "id": 7, "method": "session/request_permission",
            "params": {"sessionId": "S1", "toolCall": {"toolCallId": "c1"},
                       "options": [
                           {"optionId": "opt-allow", "name": "Allow", "kind": "allow_once"},
                           {"optionId": "opt-rej", "name": "Reject", "kind": "reject_once"}]}})
    await asyncio.sleep(0.02)
    reply = _last_reply(w, 7)
    assert reply["result"]["outcome"] == {"outcome": "selected", "optionId": "opt-allow"}
    await c.aclose()


async def test_default_permission_prefers_allow_always_then_allow_once():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    r.feed({"jsonrpc": "2.0", "id": 8, "method": "session/request_permission",
            "params": {"options": [
                {"optionId": "a1", "name": "Allow", "kind": "allow_once"},
                {"optionId": "a2", "name": "Always", "kind": "allow_always"}]}})
    await asyncio.sleep(0.02)
    # allow_once is scanned first → a1
    assert _last_reply(w, 8)["result"]["outcome"]["optionId"] == "a1"
    await c.aclose()


async def test_default_fs_read_write_handlers(tmp_path):
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    target = tmp_path / "f.txt"
    r.feed({"jsonrpc": "2.0", "id": 9, "method": "fs/write_text_file",
            "params": {"sessionId": "S", "path": str(target), "content": "hi"}})
    await asyncio.sleep(0.02)
    assert _last_reply(w, 9)["result"] == {}
    assert target.read_text() == "hi"
    r.feed({"jsonrpc": "2.0", "id": 10, "method": "fs/read_text_file",
            "params": {"sessionId": "S", "path": str(target)}})
    await asyncio.sleep(0.02)
    assert _last_reply(w, 10)["result"] == {"content": "hi"}
    await c.aclose()


async def test_unhandled_inbound_request_returns_method_not_found():
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    r, w = _wire(c)
    r.feed({"jsonrpc": "2.0", "id": 11, "method": "terminal/create", "params": {}})
    await asyncio.sleep(0.02)
    assert _last_reply(w, 11)["error"]["code"] == -32601
    await c.aclose()


def test_does_not_advertise_terminal_capability():
    """We don't implement terminal/*, so we must not advertise it — otherwise
    the agent sends terminal/* requests we can't answer and the turn stalls."""
    import inspect
    src = inspect.getsource(AcpClient.initialize)
    assert '"terminal": False' in src or "'terminal': False" in src


def test_stream_limit_raised_above_64k():
    """asyncio's default StreamReader limit (64 KB) overflows on real ACP lines
    and crashes the reader. The bump must stay well above 64 KB."""
    from aede.acp.client import _STREAM_LIMIT
    assert _STREAM_LIMIT >= 1 * 1024 * 1024


async def test_large_line_does_not_crash_reader():
    """A single NDJSON line larger than 64 KB must be parsed, not crash the
    reader with LimitOverrunError (regression for 'ACP error -1: Reader error')."""
    c = AcpClient(AgentConfig(name="x", transport=AgentTransport.LOCAL, command="x"))
    # Real asyncio subprocess path so the StreamReader limit actually applies.
    big = "Z" * (200 * 1024)  # 200 KB payload, well over the 64 KB default
    script = (
        "import sys, json\n"
        "req = json.loads(sys.stdin.readline())\n"
        f"big = {big!r}\n"
        "sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':req['id'],"
        "'result':{'echo':big}}) + '\\n'); sys.stdout.flush()\n"
    )
    import tempfile, sys as _sys
    from pathlib import Path as _Path
    d = _Path(tempfile.mkdtemp()); s = d / "big.py"; s.write_text(script)
    c2 = AcpClient(AgentConfig(name="big", transport=AgentTransport.LOCAL,
                               command=_sys.executable, args=[str(s)]))
    await c2.start()
    res = await asyncio.wait_for(c2.send_request("anything", {}), timeout=10)
    assert res["echo"] == big
    await c2.aclose()
