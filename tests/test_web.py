"""Tests for aede.tools.web SSRF prevention and size limits."""

import pytest
from unittest.mock import patch, MagicMock


def test_fetch_url_rejects_metadata_ip():
    """169.254.169.254 (cloud metadata) must be rejected before any request."""
    from aede.tools.web import fetch_url
    with pytest.raises(RuntimeError, match="private|reserved|blocked|internal"):
        fetch_url({"url": "http://169.254.169.254/latest/meta-data/"})


def test_fetch_url_rejects_private_ip():
    """Private IPv4 ranges must be rejected."""
    from aede.tools.web import fetch_url
    for ip in ("10.0.0.1", "172.16.0.1", "192.168.1.1", "127.0.0.1"):
        with pytest.raises(RuntimeError, match="private|loopback|reserved|blocked|internal"):
            fetch_url({"url": f"http://{ip}/"})


def test_fetch_url_rejects_file_scheme():
    """file:// URLs must be rejected."""
    from aede.tools.web import fetch_url
    with pytest.raises(RuntimeError, match="scheme|blocked|unsupported"):
        fetch_url({"url": "file:///etc/passwd"})


def test_fetch_url_aborts_over_size_limit():
    """Response exceeding 10 MiB must abort."""
    from aede.tools.web import fetch_url
    chunk = b"x" * 1024 * 1024
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.iter_bytes.return_value = [chunk] * 11
    mock_response.raise_for_status = MagicMock()

    with patch("aede.tools.web._validate_url", return_value="example.com"), \
         patch("httpx.stream", return_value=mock_response):
        with pytest.raises(RuntimeError, match="10 MiB|size limit|too large"):
            fetch_url({"url": "http://example.com/data"})


def test_fetch_url_public_url_success():
    """A normal public URL must fetch and return text successfully."""
    from aede.tools.web import fetch_url
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.iter_bytes.return_value = [b"hello world"]
    mock_response.raise_for_status = MagicMock()

    with patch("aede.tools.web._validate_url", return_value="example.com"), \
         patch("httpx.stream", return_value=mock_response):
        result = fetch_url({"url": "http://example.com/data"})
    assert "hello world" in result
