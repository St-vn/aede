import pytest
from pathlib import Path
import tempfile
import os


@pytest.fixture
def tmp_home(monkeypatch, tmp_path):
    """Redirect ~/.aede to a temp directory for all tests."""
    home = tmp_path / ".aede"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AEDE_HOME", str(home))
    return home
