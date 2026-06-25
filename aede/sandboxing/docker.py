from __future__ import annotations
from typing import Any, Callable
from pathlib import Path
import asyncio
import logging
import re
import threading

_log = logging.getLogger(__name__)

TOOL_NETWORK_POLICY: dict[str, str] = {
    "fetch_url": "bridge",
    "web_search": "bridge",
}

warned_once: set[str] = set()


def container_name(session_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
    return f"aede-{safe}"


class DockerSandbox:
    def __init__(self, config, project_dir, data_dir, session_id):
        self.config = config
        self.project_dir = project_dir
        self.data_dir = data_dir
        self.session_id = session_id
        self._container = None
        self._container_name = container_name(session_id)
        self._lock = threading.Lock()

    def _ensure_container(self):
        import docker
        with self._lock:
            if self._container is not None:
                try:
                    self._container.reload()
                    if self._container.status == "running":
                        return
                except Exception:
                    _log.warning("Container reload failed", exc_info=True)
                    self._container = None
        client = docker.from_env()
        network = "bridge" if self.config.sandbox_network == "bridge" else "none"
        try:
            self._container = client.containers.get(self._container_name)
        except docker.errors.NotFound:
            self._container = client.containers.run(
                self.config.sandbox_image,
                name=self._container_name,
                detach=True,
                mounts=[
                    docker.types.Mount("/workspace", str(self.project_dir), type="bind", read_only=True),
                    docker.types.Mount("/data", str(self.data_dir), type="bind", read_only=False),
                ],
                cap_add=["CHOWN", "SETUID", "SETGID"],
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true", "seccomp=default"],
                read_only=True,
                tmpfs={"/tmp": "size=64m,uid=1000"},
                pids_limit=self.config.sandbox_pids_limit,
                mem_limit=self.config.sandbox_memory,
                memswap_limit=self.config.sandbox_memory,
                nano_cpus=int(self.config.sandbox_cpus * 1e9),
                network_mode=network,
                user="1000:1000",
            )

    async def exec_cmd(self, cmd, stream_callback=None, _retries=0):
        import docker
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._ensure_container)
        except docker.errors.DockerException:
            if "docker_unavailable" not in warned_once:
                warned_once.add("docker_unavailable")
                _log.warning("Docker not available; sandbox disabled for this session")
            return -1, "Docker unavailable"
        try:
            result = await loop.run_in_executor(None, lambda: self._container.exec_run(cmd, stream=True, user="1000:1000", workdir="/workspace"))
        except docker.errors.NotFound:
            if _retries >= 1:
                raise
            self._container = None
            return await self.exec_cmd(cmd, stream_callback, _retries=_retries + 1)
        exit_code, output = result
        output_parts = []
        if hasattr(output, "__iter__") and not isinstance(output, (bytes, str)):
            for chunk in output:
                if isinstance(chunk, bytes):
                    chunk = chunk.decode("utf-8", errors="replace")
                output_parts.append(chunk)
                if stream_callback:
                    stream_callback(chunk)
        else:
            output_str = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)
            output_parts.append(output_str)
            if stream_callback:
                stream_callback(output_str)
        full_output = "".join(output_parts)
        if exit_code == 137:
            return (137, f"Command exited with code 137 (OOM). Consider raising sandbox_memory (currently {self.config.sandbox_memory}).")
        return exit_code, full_output

    def exec_cmd_sync(self, cmd, stream_callback=None):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(self.exec_cmd(cmd, stream_callback=stream_callback))
            finally:
                new_loop.close()
        return asyncio.run(self.exec_cmd(cmd, stream_callback=stream_callback))

    def translate_path(self, host_path):
        from aede.sandboxing.mounts import _host_to_container_path
        return _host_to_container_path(host_path)

    def stop(self):
        if self._container is not None:
            try:
                self._container.stop()
            except Exception:
                _log.warning("Container stop failed", exc_info=True)
            try:
                self._container.remove()
            except Exception:
                _log.warning("Container remove failed", exc_info=True)
            self._container = None

    def __del__(self):
        container = getattr(self, "_container", None)
        if container is not None:
            try:
                container.stop()
            except Exception:
                pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.stop()

