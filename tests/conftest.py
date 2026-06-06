import pytest
from pathlib import Path
import tempfile
import os


@pytest.fixture
def tmp_home(monkeypatch, tmp_path):
    """Redirect ~/.aede to a temp directory for all tests."""
    monkeypatch.setenv("AEDE_HOME", str(tmp_path / ".aede"))
    return tmp_path / ".aede"
