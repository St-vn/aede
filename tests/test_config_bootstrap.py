import pytest
from pathlib import Path


def test_bootstrap_creates_skill_agent_dirs(tmp_home):
    """bootstrap() creates skills/ and agents/ directories."""
    from aede.config import bootstrap

    bootstrap(tmp_home)

    assert (tmp_home / "skills").is_dir()
    assert (tmp_home / "agents").is_dir()


def test_bootstrap_idempotent(tmp_home):
    """bootstrap() is safe to call multiple times."""
    from aede.config import bootstrap

    bootstrap(tmp_home)
    bootstrap(tmp_home)

    assert (tmp_home / "skills").is_dir()
    assert (tmp_home / "agents").is_dir()
    assert (tmp_home / "data").is_dir()


def test_bootstrap_also_creates_data_and_config(tmp_home):
    """Existing bootstrap behaviour (data dirs + config.yml) is preserved."""
    from aede.config import bootstrap

    bootstrap(tmp_home)

    assert (tmp_home / "data").is_dir()
    assert (tmp_home / "data" / "sessions").is_dir()
    assert (tmp_home / "config.yml").exists()
