import pytest
from pathlib import Path
import tempfile
import os


@pytest.fixture
def tmp_home(monkeypatch, tmp_path):
    """Redirect ~/.jarvis to a temp directory for all tests."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / ".jarvis"))
    return tmp_path / ".jarvis"
