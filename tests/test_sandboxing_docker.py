from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging
import pytest


class TestDkr001SandboxConfigDeleted:
    @pytest.mark.asyncio
    async def test_import_raises(self):
        with pytest.raises(ImportError):
            from aede.sandboxing.docker import SandboxConfig

    @pytest.mark.asyncio
    async def test_mem_limit_from_flat_config(self):
        from aede.sandboxing.docker import DockerSandbox
        from docker.errors import NotFound
        mock_client = MagicMock()
        mock_containers = MagicMock()
        mock_container = MagicMock()
        mock_containers.get.side_effect = NotFound("not found")
        mock_containers.run.return_value = mock_container
        mock_client.containers = mock_containers
        mock_container.exec_run.return_value = (0, b"ok")
        config = MagicMock()
        config.sandbox_image = "aede-sandbox:latest"
        config.sandbox_memory = "512m"
        config.sandbox_cpus = 1.0
        config.sandbox_network = "off"
        config.sandbox_pids_limit = 256
        sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid1")
        with patch("docker.from_env", return_value=mock_client):
            await sandbox.exec_cmd(["echo", "hi"])
        _, kwargs = mock_containers.run.call_args
        assert kwargs.get("mem_limit") == "512m"


class TestDkr002MemswapLimit:
    @pytest.mark.asyncio
    async def test_memswap_limit_equals_mem_limit(self):
        from aede.sandboxing.docker import DockerSandbox
        from docker.errors import NotFound
        mock_client = MagicMock()
        mock_containers = MagicMock()
        mock_container = MagicMock()
        mock_containers.get.side_effect = NotFound("not found")
        mock_containers.run.return_value = mock_container
        mock_client.containers = mock_containers
        mock_container.exec_run.return_value = (0, b"ok")
        config = MagicMock()
        config.sandbox_image = "aede-sandbox:latest"
        config.sandbox_memory = "1g"
        config.sandbox_cpus = 1.0
        config.sandbox_network = "off"
        config.sandbox_pids_limit = 256
        sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid2")
        with patch("docker.from_env", return_value=mock_client):
            await sandbox.exec_cmd(["echo", "hi"])
        _, kwargs = mock_containers.run.call_args
        assert kwargs.get("memswap_limit") == "1g"
        assert kwargs["memswap_limit"] == kwargs["mem_limit"]


class TestDkr005StopFailuresLogged:
    def test_stop_failures_logged(self, caplog):
        from aede.sandboxing.docker import DockerSandbox
        mock_container = MagicMock()
        mock_container.stop.side_effect = RuntimeError("stop failed")
        mock_container.remove.side_effect = RuntimeError("remove failed")
        config = MagicMock()
        config.sandbox_image = "aede-sandbox:latest"
        config.sandbox_memory = "512m"
        config.sandbox_cpus = 1.0
        config.sandbox_network = "off"
        config.sandbox_pids_limit = 256
        sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid3")
        sandbox._container = mock_container
        caplog.set_level(logging.WARNING)
        sandbox.stop()
        messages = [r.message for r in caplog.records]
        assert any("stop failed" in m for m in messages)
        assert any("remove failed" in m for m in messages)


class TestDkr008Cleanup:
    @pytest.mark.asyncio
    async def test_aexit_calls_stop_and_remove(self):
        from aede.sandboxing.docker import DockerSandbox
        mock_container = MagicMock()
        config = MagicMock()
        config.sandbox_image = "aede-sandbox:latest"
        config.sandbox_memory = "512m"
        config.sandbox_cpus = 1.0
        config.sandbox_network = "off"
        config.sandbox_pids_limit = 256
        sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid4")
        sandbox._container = mock_container
        async with sandbox as ctx:
            assert ctx is sandbox
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()

    def test_del_attempts_stop(self):
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
        del sandbox
        mock_container.stop.assert_called_once()


class TestDkr006BoundedRetry:
    @pytest.mark.asyncio
    async def test_not_found_retry_then_raise(self):
        from aede.sandboxing.docker import DockerSandbox
        from docker.errors import NotFound
        mock_client = MagicMock()
        mock_containers = MagicMock()
        mock_container = MagicMock()
        mock_containers.get.side_effect = NotFound("not found")
        mock_containers.run.return_value = mock_container
        mock_client.containers = mock_containers
        mock_container.exec_run.side_effect = NotFound("container gone")
        config = MagicMock()
        config.sandbox_image = "aede-sandbox:latest"
        config.sandbox_memory = "512m"
        config.sandbox_cpus = 1.0
        config.sandbox_network = "off"
        config.sandbox_pids_limit = 256
        sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid6")
        with patch("docker.from_env", return_value=mock_client):
            with pytest.raises(NotFound):
                await sandbox.exec_cmd(["echo", "hi"])
        assert mock_container.exec_run.call_count == 2
        assert mock_containers.run.call_count == 2


class TestDkr007ThreadSafety:
    def test_lock_prevents_duplicate_container(self):
        from aede.sandboxing.docker import DockerSandbox
        from docker.errors import NotFound
        from concurrent.futures import ThreadPoolExecutor
        import threading
        mock_client = MagicMock()
        mock_containers = MagicMock()
        mock_container = MagicMock()
        mock_containers.get.side_effect = NotFound("not found")
        mock_client.containers = mock_containers
        mock_container.status = "running"
        mock_container.reload.return_value = None
        run_count = []
        run_lock = threading.Lock()
        def counting_run(*args, **kwargs):
            with run_lock:
                run_count.append(1)
            return mock_container
        mock_containers.run.side_effect = counting_run
        config = MagicMock()
        config.sandbox_image = "aede-sandbox:latest"
        config.sandbox_memory = "512m"
        config.sandbox_cpus = 1.0
        config.sandbox_network = "off"
        config.sandbox_pids_limit = 256
        sandbox = DockerSandbox(config, Path("/tmp/proj"), Path("/tmp/data"), "sid7")
        barrier = threading.Barrier(2)
        def call_ensure():
            barrier.wait()
            sandbox._ensure_container()
        with patch("docker.from_env", return_value=mock_client):
            with ThreadPoolExecutor(max_workers=2) as pool:
                f1 = pool.submit(call_ensure)
                f2 = pool.submit(call_ensure)
                f1.result(timeout=5)
                f2.result(timeout=5)
        assert len(run_count) == 1
