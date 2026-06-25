from __future__ import annotations
from pathlib import Path
import pytest


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
