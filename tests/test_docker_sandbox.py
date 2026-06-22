from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_container_name_formatting():
    from aede.sandboxing.docker import container_name
    name = container_name("session_abc")
    assert name == "aede-session_abc"


def test_container_name_sanitizes():
    from aede.sandboxing.docker import container_name
    name = container_name("bad/name:chars!")
    assert "/" not in name
    assert ":" not in name
    assert "!" not in name


def test_init_stores_config():
    from aede.sandboxing.docker import DockerSandbox

    config = MagicMock()
    config.sandbox_image = "aede-sandbox:latest"
    config.sandbox_memory = "512m"
    config.sandbox_cpus = 1.0
    config.sandbox_network = "off"
    config.sandbox_pids_limit = 256

    project_dir = Path("/tmp/project")
    data_dir = Path("/tmp/data")
    sandbox = DockerSandbox(config, project_dir, data_dir, "test-sid-123")

    assert sandbox.config is config
    assert sandbox.project_dir == project_dir
    assert sandbox.data_dir == data_dir
    assert sandbox.session_id == "test-sid-123"
    assert sandbox._container is None
    assert sandbox._container_name == "aede-test-sid-123"


@pytest.mark.asyncio
async def test_exec_cmd_creates_container_on_first_call():
    from aede.sandboxing.docker import DockerSandbox
    from docker.errors import NotFound

    mock_client = MagicMock()
    mock_containers = MagicMock()
    mock_container = MagicMock()

    mock_containers.get.side_effect = NotFound("not found")
    mock_containers.run.return_value = mock_container
    mock_client.containers = mock_containers

    mock_container.exec_run.return_value = (0, b"hello world")

    config = MagicMock()
    config.sandbox_image = "aede-sandbox:latest"
    config.sandbox_memory = "512m"
    config.sandbox_cpus = 1.0
    config.sandbox_network = "off"
    config.sandbox_pids_limit = 256

    sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid1")

    with patch("docker.from_env", return_value=mock_client):
        exit_code, output = await sandbox.exec_cmd(["echo", "hello"])

    assert exit_code == 0
    assert output == "hello world"
    mock_containers.run.assert_called_once()
    mock_container.exec_run.assert_called_once()


@pytest.mark.asyncio
async def test_exec_cmd_reuses_warm_container():
    from aede.sandboxing.docker import DockerSandbox

    mock_client = MagicMock()
    mock_containers = MagicMock()
    mock_container = MagicMock()

    # warm container: needs status="running" and reload()
    mock_container.status = "running"
    mock_container.reload.return_value = None
    mock_container.exec_run.return_value = (0, b"output text")
    mock_client.containers = mock_containers

    config = MagicMock()
    config.sandbox_image = "aede-sandbox:latest"
    config.sandbox_memory = "512m"
    config.sandbox_cpus = 1.0
    config.sandbox_network = "off"
    config.sandbox_pids_limit = 256

    sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid2")
    sandbox._container = mock_container  # already started

    with patch("docker.from_env", return_value=mock_client):
        exit_code, output = await sandbox.exec_cmd(["echo", "hi"])

    assert exit_code == 0
    assert output == "output text"
    mock_containers.run.assert_not_called()
    mock_container.exec_run.assert_called_once()


@pytest.mark.asyncio
async def test_warned_once_suppresses_repeated_docker_warnings():
    from aede.sandboxing.docker import DockerSandbox, warned_once
    from docker.errors import DockerException
    warned_once.clear()

    config = MagicMock()
    config.sandbox_image = "aede-sandbox:latest"
    config.sandbox_memory = "512m"
    config.sandbox_cpus = 1.0
    config.sandbox_network = "off"
    config.sandbox_pids_limit = 256

    sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid3")

    with patch("docker.from_env", side_effect=DockerException("conn refused")):
        exit_code_1, output_1 = await sandbox.exec_cmd(["echo", "hi"])
        assert exit_code_1 == -1
        assert "docker_unavailable" in warned_once

        warned_len_before = len(warned_once)
        exit_code_2, output_2 = await sandbox.exec_cmd(["echo", "hi"])
        assert len(warned_once) == warned_len_before
        assert exit_code_2 == -1


def test_translate_path_delegates_to_mounts():
    from aede.sandboxing.docker import DockerSandbox

    config = MagicMock()
    config.sandbox_image = "aede-sandbox:latest"
    config.sandbox_memory = "512m"
    config.sandbox_cpus = 1.0
    config.sandbox_network = "off"
    config.sandbox_pids_limit = 256

    sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid4")

    with patch(
        "aede.sandboxing.mounts._host_to_container_path", return_value="/mnt/c/foo/bar"
    ) as mock_translate:
        result = sandbox.translate_path(Path(r"C:\foo\bar"))
        assert result == "/mnt/c/foo/bar"
        mock_translate.assert_called_once_with(Path(r"C:\foo\bar"))


def test_stop_calls_container_stop_and_remove():
    from aede.sandboxing.docker import DockerSandbox

    mock_container = MagicMock()

    config = MagicMock()
    config.sandbox_image = "aede-sandbox:latest"
    config.sandbox_memory = "512m"
    config.sandbox_cpus = 1.0
    config.sandbox_network = "off"
    config.sandbox_pids_limit = 256

    sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid5")
    sandbox._container = mock_container

    sandbox.stop()
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()


def test_stop_noop_when_no_container():
    from aede.sandboxing.docker import DockerSandbox

    config = MagicMock()
    config.sandbox_image = "aede-sandbox:latest"
    config.sandbox_memory = "512m"
    config.sandbox_cpus = 1.0
    config.sandbox_network = "off"
    config.sandbox_pids_limit = 256

    sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid6")
    # _container is None — should not raise
    sandbox.stop()
