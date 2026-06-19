from unittest.mock import MagicMock
from aede.cli import _handle_esc_key


def test_esc_key_requests_stop():
    loop = MagicMock()
    assert _handle_esc_key(loop) is True
    loop.request_stop.assert_called_once()


def test_esc_key_no_loop():
    assert _handle_esc_key(None) is False
