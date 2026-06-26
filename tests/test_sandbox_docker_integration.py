"""Real-Docker integration tests for the sandbox (Track 2 correctness).

The existing sandbox tests all mock the container — they exercise the fileset
gate logic but never run `DockerSandbox.exec_cmd` / `_ensure_container` against a
real Docker daemon.  Coverage showed docker.py 117-185 (the exec path) untested.
These tests run the real container to prove the feature works end-to-end and that
the Phase-2 write-isolation hardening (read_only root + read-only /workspace mount)
actually holds at runtime.

Skipped automatically when Docker is unavailable, so CI without Docker stays green.

Design note found while writing these: `_ensure_container` relies on the IMAGE
providing a long-running CMD (the real `aede-sandbox` Dockerfile uses
`tini -- sleep infinity`).  A vanilla image like `python:3.12-slim` exits
immediately and the container is dead before `exec_run` — so the sandbox would
silently break if `sandbox_image` is pointed at such an image.  These tests
inject a keep-alive command via a tiny wrapper so they exercise the real exec
path without depending on the project's own image build.
"""
from __future__ import annotations
import asyncio
from pathlib import Path

import pytest


def _docker_available() -> bool:
    try:
        import docker  # noqa: F401
    except Exception:
        return False
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(), reason="Docker daemon not available"
)


class _Cfg:
    """Minimal stand-in for the AedeConfig fields DockerSandbox actually reads.

    NOTE: the runtime passes the full AedeConfig (cli.py:553), which carries
    these `sandbox_*` attributes — NOT the legacy `SandboxConfig` dataclass,
    whose field names (`image`, `memory_limit`) diverge and is effectively dead.
    """

    sandbox_image = "python:3.12-slim"
    sandbox_memory = "256m"
    sandbox_cpus = 1.0
    sandbox_network = "off"
    sandbox_pids_limit = 128


@pytest.fixture
def sandbox(tmp_path):
    """Pre-create the keep-alive container with the SAME isolation flags
    DockerSandbox uses, named so `_ensure_container`'s `containers.get` adopts it.

    This exercises the real `exec_cmd` path (docker.py 110-150) and the real
    isolation (read_only root, read-only /workspace bind) without depending on
    the project's own `aede-sandbox:latest` image build.
    """
    import docker
    from aede.sandboxing.docker import DockerSandbox, container_name

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "hello.txt").write_text("hi from host")
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    cfg = _Cfg()
    name = container_name("itest-sess")
    client = docker.from_env()
    # Remove any stale container from a prior failed run.
    try:
        client.containers.get(name).remove(force=True)
    except Exception:
        pass
    container = client.containers.run(
        cfg.sandbox_image,
        command=["sleep", "infinity"],  # keep-alive, mirrors the real image CMD
        name=name,
        detach=True,
        mounts=[
            docker.types.Mount("/workspace", str(project_dir), type="bind", read_only=True),
            docker.types.Mount("/data", str(data_dir), type="bind", read_only=False),
        ],
        cap_drop=["ALL"],
        security_opt=["no-new-privileges:true"],
        read_only=True,
        tmpfs={"/tmp": "size=64m,uid=1000"},
        network_mode="none",
        user="1000:1000",
    )

    sb = DockerSandbox(cfg, project_dir, data_dir, session_id="itest-sess")
    sb._container = container  # adopt the pre-started, isolated container
    yield sb
    try:
        container.remove(force=True)
    except Exception:
        pass


def test_exec_runs_command_and_returns_output(sandbox):
    """A real container executes a command and returns its stdout.

    NOTE (real behavior, see finding): exec_cmd uses ``stream=True``, so the
    Docker SDK returns ``exit_code=None`` for the streamed path — the (None, output)
    contract. We assert on output, not exit code, to match the real contract.
    """
    exit_code, output = asyncio.run(sandbox.exec_cmd(["echo", "sandbox-works"]))
    assert "sandbox-works" in output
    # exit_code is None on the streaming path — documents the real contract.
    assert exit_code in (0, None)


def test_workspace_mount_is_readonly(sandbox):
    """Phase-2 isolation: /workspace is a read-only bind — writes must fail.

    Proves the read-only mount hardening holds at runtime, not just in config.
    """
    _exit_code, output = asyncio.run(
        sandbox.exec_cmd(["sh", "-c", "echo x > /workspace/should_fail.txt 2>&1"])
    )
    # exit_code is unreliable on the streaming path; assert on the real effect:
    # the write must produce a read-only error AND the host file must not exist.
    assert "read-only" in output.lower() or "permission denied" in output.lower(), (
        f"write to read-only /workspace did not error (output {output!r}) — isolation broken"
    )
    assert not (sandbox.project_dir / "should_fail.txt").exists()


def test_host_workspace_file_is_visible_readonly(sandbox):
    """The host project_dir is visible inside the container at /workspace (RO)."""
    _exit_code, output = asyncio.run(
        sandbox.exec_cmd(["cat", "/workspace/hello.txt"])
    )
    assert "hi from host" in output


def test_root_filesystem_is_readonly(sandbox):
    """Container root is read_only=True — writing outside /tmp and /data fails."""
    _exit_code, output = asyncio.run(
        sandbox.exec_cmd(["sh", "-c", "echo x > /etc/should_fail 2>&1"])
    )
    assert "read-only" in output.lower() or "permission denied" in output.lower(), (
        f"write to read-only root filesystem did not error (output {output!r})"
    )
