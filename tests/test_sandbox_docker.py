from __future__ import annotations
from pathlib import Path
import pytest


def test_sandbox_disabled_by_default():
    from aede.sandboxing.docker import SandboxConfig
    cfg = SandboxConfig()
    assert cfg.enabled is False


def test_sandbox_config_defaults():
    from aede.sandboxing.docker import SandboxConfig
    cfg = SandboxConfig()
    assert cfg.image == "python:3.12-slim"
    assert cfg.workspace_mount == "/workspace"
    assert cfg.memory_limit == "512m"
    assert cfg.cpu_limit == 1.0


def test_sandbox_config_from_dict():
    from aede.sandboxing.docker import SandboxConfig
    raw = {"enabled": True, "image": "custom:latest", "memory_limit": "1g", "cpu_limit": 2.0}
    cfg = SandboxConfig.from_dict(raw)
    assert cfg.enabled is True
    assert cfg.image == "custom:latest"
    assert cfg.memory_limit == "1g"
    assert cfg.cpu_limit == 2.0


def test_mount_builds_docker_mount(tmp_path):
    from aede.sandboxing.mounts import Mount
    m = Mount(source=tmp_path, target="/workspace", read_only=True)
    docker_mount = m.to_docker_mount()
    assert docker_mount["Source"] == str(tmp_path)
    assert docker_mount["Target"] == "/workspace"
    assert docker_mount["ReadOnly"] is True


def test_mount_default_read_write(tmp_path):
    from aede.sandboxing.mounts import Mount
    m = Mount(source=tmp_path, target="/data")
    docker_mount = m.to_docker_mount()
    assert docker_mount["ReadOnly"] is False


def test_mount_type_defaults_to_bind(tmp_path):
    from aede.sandboxing.mounts import Mount
    m = Mount(source=tmp_path, target="/mnt")
    assert m.type == "bind"


@pytest.mark.skip(reason="Docker SDK not available in CI; unit test for config only")
def test_sandbox_create_container():
    pass


def test_sandbox_container_name_includes_session_id():
    from aede.sandboxing.docker import container_name
    name = container_name("session_abc123")
    assert "session_abc123" in name
    assert name.startswith("aede-")


def test_sandbox_container_name_sanitizes():
    from aede.sandboxing.docker import container_name
    name = container_name("bad/name:chars!")
    assert "/" not in name
    assert ":" not in name
    assert "!" not in name


def test_sandbox_config_from_dict_partial():
    from aede.sandboxing.docker import SandboxConfig
    raw = {"enabled": True}
    cfg = SandboxConfig.from_dict(raw)
    assert cfg.enabled is True
    assert cfg.image == "python:3.12-slim"


def test_sandbox_config_from_dict_empty():
    from aede.sandboxing.docker import SandboxConfig
    cfg = SandboxConfig.from_dict({})
    assert cfg.enabled is False
