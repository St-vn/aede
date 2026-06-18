from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from pathlib import Path
import asyncio
import re

TOOL_NETWORK_POLICY: dict[str, str] = {
    "fetch_url": "bridge",
    "web_search": "bridge",
}

warned_once: set[str] = set()


@dataclass
class SandboxConfig:
    enabled: bool = False
    image: str = "python:3.12-slim"
    workspace_mount: str = "/workspace"
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SandboxConfig:
        return cls(
            enabled=raw.get("enabled", False),
            image=raw.get("image", "python:3.12-slim"),
            workspace_mount=raw.get("workspace_mount", "/workspace"),
            memory_limit=raw.get("memory_limit", "512m"),
            cpu_limit=float(raw.get("cpu_limit", 1.0)),
            env=raw.get("env", {}),
        )


def container_name(session_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
    return f"aede-{safe}"


class DockerSandbox:
    def __init__(self, config, project_dir: Path, data_dir: Path, session_id: str):
        self.config = config
        self.project_dir = project_dir
        self.data_dir = data_dir
        self.session_id = session_id
        self._container = None
        self._container_name = container_name(session_id)

    def _ensure_container(self) -> None:
        import docker

        if self._container is not None:
            try:
                self._container.reload()
                if self._container.status == "running":
                    return
            except Exception:
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
                    docker.types.Mount(
                        "/workspace", str(self.project_dir), type="bind", read_only=True
                    ),
                    docker.types.Mount(
                        "/data", str(self.data_dir), type="bind", read_only=False
                    ),
                ],
                cap_add=["CHOWN", "SETUID", "SETGID"],
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true", "seccomp=default"],
                read_only=True,
                tmpfs={"/tmp": "size=64m,uid=1000"},
                pids_limit=self.config.sandbox_pids_limit,
                mem_limit=self.config.sandbox_memory,
                nano_cpus=int(self.config.sandbox_cpus * 1e9),
                network_mode=network,
                user="1000:1000",
            )

    async def exec_cmd(
        self, cmd: list[str], stream_callback: Callable[[str], None] | None = None
    ) -> tuple[int, str]:
        import docker

        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(None, self._ensure_container)
        except docker.errors.DockerException:
            if "docker_unavailable" not in warned_once:
                warned_once.add("docker_unavailable")
                print(
                    "\n[!] Docker not available; sandbox disabled for this session. "
                    "Install Docker Desktop for hardened isolation.\n"
                )
            return -1, "Docker unavailable"

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._container.exec_run(
                    cmd, stream=True, user="1000:1000", workdir="/workspace"
                ),
            )
        except docker.errors.NotFound:
            self._container = None
            return await self.exec_cmd(cmd, stream_callback)

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
            output_str = (
                output.decode("utf-8", errors="replace")
                if isinstance(output, bytes)
                else str(output)
            )
            output_parts.append(output_str)
            if stream_callback:
                stream_callback(output_str)

        full_output = "".join(output_parts)

        if exit_code == 137:
            return (
                137,
                f"Command exited with code 137 (OOM). "
                f"Consider raising sandbox_memory (currently {self.config.sandbox_memory}).",
            )

        return exit_code, full_output

    def exec_cmd_sync(
        self, cmd: list[str], stream_callback: Callable[[str], None] | None = None
    ) -> tuple[int, str]:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(
                    self.exec_cmd(cmd, stream_callback=stream_callback)
                )
            finally:
                new_loop.close()
        return asyncio.run(self.exec_cmd(cmd, stream_callback=stream_callback))

    def translate_path(self, host_path: Path) -> str:
        from aede.sandboxing.mounts import _host_to_container_path

        return _host_to_container_path(host_path)

    def stop(self) -> None:
        if self._container is not None:
            try:
                self._container.stop()
            except Exception:
                pass
            try:
                self._container.remove()
            except Exception:
                pass
            self._container = None
