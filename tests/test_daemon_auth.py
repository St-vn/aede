"""
US-SEC-6 — Daemon control port requires authentication (DMN-E-1).

Scenarios covered:
  6.1 — Unauthenticated command is rejected before dispatch.
  6.2 — Authenticated command (token from daemon.token) is accepted.
NFRs:
  - Unbounded readline is capped (oversized payload rejected, no crash).
  - Exception responses do not leak internal paths/tracebacks.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from pathlib import Path

from aede.daemon import Daemon, send_command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _raw_send(port: int, payload: bytes) -> bytes:
    """Open a raw connection to the daemon, send raw bytes, read one line."""
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(payload)
    await writer.drain()
    data = await reader.readline()
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass
    return data


def _read_port(data_dir: Path) -> int:
    return int((data_dir / "daemon.port").read_text().strip())


def _read_token(data_dir: Path) -> str:
    return (data_dir / "daemon.token").read_text().strip()


# ---------------------------------------------------------------------------
# Scenario 6.1 — Unauthenticated command is rejected before dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthenticated_command_rejected(tmp_home):
    """Without a token the command must be rejected and NOT dispatched."""
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        port = _read_port(tmp_home)
        # Send a valid JSON command but with NO token field.
        payload = (json.dumps({"cmd": "ping"}) + "\n").encode()
        raw = await _raw_send(port, payload)
        resp = json.loads(raw.decode())

        # Must be rejected — status == "error" or status == "unauthorized".
        assert resp.get("status") in ("error", "unauthorized"), (
            f"Expected rejection, got: {resp}"
        )
        # The "pong" field must NOT be present (command was not dispatched).
        assert "pong" not in resp, (
            "Command was dispatched despite missing auth token"
        )
    finally:
        await d.stop()


@pytest.mark.asyncio
async def test_wrong_token_rejected(tmp_home):
    """A wrong token must be rejected."""
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        port = _read_port(tmp_home)
        payload = (json.dumps({"cmd": "ping", "token": "wrong-token"}) + "\n").encode()
        raw = await _raw_send(port, payload)
        resp = json.loads(raw.decode())
        assert resp.get("status") in ("error", "unauthorized"), (
            f"Expected rejection with wrong token, got: {resp}"
        )
        assert "pong" not in resp
    finally:
        await d.stop()


# ---------------------------------------------------------------------------
# Scenario 6.2 — Authenticated command (correct token) is accepted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticated_command_accepted(tmp_home):
    """Correct token from daemon.token file must let the command through."""
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        # Token file must exist after start().
        token_path = tmp_home / "daemon.token"
        assert token_path.exists(), "daemon.token was not created on start()"

        token = _read_token(tmp_home)
        assert len(token) >= 16, "Token is suspiciously short"

        port = _read_port(tmp_home)
        payload = (json.dumps({"cmd": "ping", "token": token}) + "\n").encode()
        raw = await _raw_send(port, payload)
        resp = json.loads(raw.decode())

        assert resp.get("status") == "ok", f"Authenticated ping failed: {resp}"
        assert resp.get("pong") is True
    finally:
        await d.stop()


@pytest.mark.asyncio
async def test_token_file_cleaned_up_on_stop(tmp_home):
    """daemon.token must be deleted when the daemon stops."""
    d = Daemon(data_dir=tmp_home)
    await d.start()
    token_path = tmp_home / "daemon.token"
    assert token_path.exists()
    await d.stop()
    assert not token_path.exists(), "daemon.token was not removed on stop()"


# ---------------------------------------------------------------------------
# send_command helper sends the token automatically
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_command_helper_authenticates(tmp_home):
    """The send_command() helper must embed the token so existing callers work."""
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        resp = await send_command({"cmd": "ping"}, data_dir=tmp_home)
        assert resp.get("status") == "ok"
        assert resp.get("pong") is True
    finally:
        await d.stop()


# ---------------------------------------------------------------------------
# NFR — Oversized payload is rejected (unbounded readline cap)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_oversized_payload_rejected(tmp_home):
    """An oversized line must be rejected without crashing the daemon."""
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        token = _read_token(tmp_home)
        port = _read_port(tmp_home)
        # Build a payload bigger than any reasonable limit (e.g. 1 MB).
        oversized = b"x" * (1024 * 1024) + b"\n"
        try:
            raw = await asyncio.wait_for(_raw_send(port, oversized), timeout=5.0)
            # If we get a response it must be an error, not a crash.
            if raw:
                resp = json.loads(raw.decode())
                assert resp.get("status") == "error"
        except (asyncio.TimeoutError, ConnectionError, json.JSONDecodeError):
            # Connection reset / timeout is also acceptable rejection behaviour.
            pass

        # Daemon must still be alive after the oversized attempt.
        port2 = _read_port(tmp_home)
        payload = (json.dumps({"cmd": "ping", "token": token}) + "\n").encode()
        raw2 = await _raw_send(port2, payload)
        resp2 = json.loads(raw2.decode())
        assert resp2.get("status") == "ok", "Daemon crashed after oversized payload"
    finally:
        await d.stop()


# ---------------------------------------------------------------------------
# NFR — Error responses must not leak tracebacks / internal paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_error_response_does_not_leak_internals(tmp_home):
    """Error messages returned to the client must be generic, not tracebacks."""
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        token = _read_token(tmp_home)
        port = _read_port(tmp_home)
        # Corrupt JSON — will trigger a parse error inside the handler.
        payload = b"{bad json\n"
        raw = await _raw_send(port, payload)
        if raw:
            resp = json.loads(raw.decode())
            msg = resp.get("message", "")
            # Must not contain path separators or "Traceback" keywords.
            assert "Traceback" not in msg
            assert "aede" not in msg
            assert "\\" not in msg
            assert "/" not in msg or msg.count("/") == 0
    finally:
        await d.stop()
