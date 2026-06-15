import pytest
from unittest.mock import patch, MagicMock


def test_parse_config_raw():
    from aede.commands import parse_command
    result = parse_command("/config raw")
    assert result is not None
    assert result.name == "config"
    assert result.args == ["raw"]


def test_handle_config_raw_opens_global(tmp_home):
    from aede.commands import handle_config_edit
    cfg = MagicMock()
    console = MagicMock()
    home = tmp_home
    project_dir = tmp_home

    with patch("aede.config.edit_config_file") as mock_edit:
        handle_config_edit(["raw"], cfg, console, home, project_dir)
        mock_edit.assert_called_once_with("global", home=home, project_dir=project_dir)


def test_handle_config_raw_with_project_opens_project(tmp_home, tmp_path):
    from aede.commands import handle_config_edit
    cfg = MagicMock()
    console = MagicMock()
    home = tmp_home
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    with patch("aede.config.edit_config_file") as mock_edit:
        handle_config_edit(["raw", "project"], cfg, console, home, project_dir)
        mock_edit.assert_called_once_with("project", home=home, project_dir=project_dir)
