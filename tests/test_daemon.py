import pytest
import sys
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from aede.daemon import Daemon, send_command


def test_daemon_init(tmp_home):
    d = Daemon(data_dir=tmp_home)
    assert d.data_dir == tmp_home
    assert d._running is False


def test_daemon_not_running_initially(tmp_home):
    d = Daemon(data_dir=tmp_home)
    assert d.is_running() is False


def test_daemon_pid_path(tmp_home):
    d = Daemon(data_dir=tmp_home)
    assert d.pid_path == tmp_home / "daemon.pid"


def test_daemon_port_path(tmp_home):
    d = Daemon(data_dir=tmp_home)
    assert d.port_path == tmp_home / "daemon.port"


def test_daemon_is_running_returns_true_when_pid_file_and_process_exists(tmp_home):
    d = Daemon(data_dir=tmp_home)
    d.pid_path.write_text(str(999999999))
    with patch("aede.daemon._process_exists", return_value=True):
        assert d.is_running() is True


def test_daemon_is_running_returns_false_when_pid_file_missing(tmp_home):
    d = Daemon(data_dir=tmp_home)
    assert d.is_running() is False


def test_daemon_is_running_returns_false_when_process_dead(tmp_home):
    d = Daemon(data_dir=tmp_home)
    d.pid_path.write_text(str(999999999))
    with patch("aede.daemon._process_exists", return_value=False):
        assert d.is_running() is False


@pytest.mark.asyncio
async def test_daemon_start_stop(tmp_home):
    d = Daemon(data_dir=tmp_home)
    assert d._running is False
    await d.start()
    assert d._running is True
    assert d.pid_path.exists()
    pid = int(d.pid_path.read_text().strip())
    assert pid > 0
    await d.stop()
    assert d._running is False


@pytest.mark.asyncio
async def test_daemon_double_start_raises(tmp_home):
    d = Daemon(data_dir=tmp_home)
    await d.start()
    with pytest.raises(RuntimeError, match="already running"):
        await d.start()
    await d.stop()


@pytest.mark.asyncio
async def test_daemon_ping_command(tmp_home):
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        resp = await send_command({"cmd": "ping"}, data_dir=tmp_home)
        assert resp["status"] == "ok"
        assert "pong" in resp
    finally:
        await d.stop()


@pytest.mark.asyncio
async def test_daemon_status_command(tmp_home):
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        resp = await send_command({"cmd": "status"}, data_dir=tmp_home)
        assert resp["status"] == "ok"
        assert "pid" in resp
        assert resp["running"] is True
    finally:
        await d.stop()


@pytest.mark.asyncio
async def test_daemon_stop_command(tmp_home):
    d = Daemon(data_dir=tmp_home)
    await d.start()
    assert d._running is True
    resp = await send_command({"cmd": "stop"}, data_dir=tmp_home)
    assert resp["status"] == "ok"
    await asyncio.sleep(0.1)
    assert d._running is False


@pytest.mark.asyncio
async def test_daemon_unknown_command_returns_error(tmp_home):
    d = Daemon(data_dir=tmp_home)
    await d.start()
    try:
        resp = await send_command({"cmd": "explode"}, data_dir=tmp_home)
        assert resp["status"] == "error"
    finally:
        await d.stop()


@pytest.mark.asyncio
async def test_send_command_to_nonexistent_daemon_raises(tmp_home):
    d = Daemon(data_dir=tmp_home)
    assert d.is_running() is False
    with pytest.raises(ConnectionError):
        await send_command({"cmd": "ping"}, data_dir=tmp_home)


def test_process_exists_with_live_pid():
    from aede.daemon import _process_exists
    assert _process_exists(0) is False  # pid 0 never exists
