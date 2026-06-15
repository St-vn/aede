import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from aede.observability.fde_capture import FdeCapture


class TestFdeCaptureDisabled:
    def test_noop_when_disabled(self, tmp_path):
        capture = FdeCapture(enabled=False, data_dir=tmp_path)
        capture.capture_tool_call(
            session_id="sess_001",
            turn_number=1,
            tool_name="read_file",
            tool_args={"path": "/tmp/x"},
            tool_result="file content",
            outcome="success",
            latency_ms=42,
        )
        fde_dir = tmp_path / "fde"
        assert not fde_dir.exists()


class TestFdeCaptureEnabled:
    def test_writes_jsonl_when_enabled(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        capture.capture_tool_call(
            session_id="sess_001",
            turn_number=1,
            tool_name="read_file",
            tool_args={"path": "/tmp/x"},
            tool_result="file content",
            outcome="success",
            latency_ms=42,
        )
        fde_path = tmp_path / "fde" / "sess_001.jsonl"
        assert fde_path.exists()
        lines = fde_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["tool_name"] == "read_file"
        assert record["outcome"] == "success"
        assert record["latency_ms"] == 42
        assert record["turn_number"] == 1
        assert "timestamp" in record
        assert record["schema_version"] == "fde-v1"

    def test_multiple_calls_append(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        capture.capture_tool_call(session_id="sess_001", turn_number=1, tool_name="read_file",
                                  tool_args={}, tool_result="a", outcome="success", latency_ms=10)
        capture.capture_tool_call(session_id="sess_001", turn_number=2, tool_name="write_file",
                                  tool_args={}, tool_result="b", outcome="success", latency_ms=20)
        fde_path = tmp_path / "fde" / "sess_001.jsonl"
        lines = fde_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

    def test_different_session_separate_files(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        capture.capture_tool_call(session_id="sess_a", turn_number=1, tool_name="read_file",
                                  tool_args={}, tool_result="a", outcome="success", latency_ms=10)
        capture.capture_tool_call(session_id="sess_b", turn_number=1, tool_name="write_file",
                                  tool_args={}, tool_result="b", outcome="success", latency_ms=20)
        assert (tmp_path / "fde" / "sess_a.jsonl").exists()
        assert (tmp_path / "fde" / "sess_b.jsonl").exists()


class TestFdeCaptureRedaction:
    def test_args_redacted_before_capture(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        capture.capture_tool_call(
            session_id="sess_001",
            turn_number=1,
            tool_name="web_search",
            tool_args={"query": "my email is user@example.com"},
            tool_result="results",
            outcome="success",
            latency_ms=100,
        )
        fde_path = tmp_path / "fde" / "sess_001.jsonl"
        record = json.loads(fde_path.read_text(encoding="utf-8"))
        assert "@" not in record["tool_args"]["query"]

    def test_result_redacted_before_capture(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        capture.capture_tool_call(
            session_id="sess_001",
            turn_number=1,
            tool_name="read_file",
            tool_args={"path": "/tmp/x"},
            tool_result="api_key=sk-test-key-12345",
            outcome="success",
            latency_ms=10,
        )
        fde_path = tmp_path / "fde" / "sess_001.jsonl"
        record = json.loads(fde_path.read_text(encoding="utf-8"))
        assert "sk-test-key" not in record["tool_result"]

    def test_tool_name_not_redacted(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        capture.capture_tool_call(
            session_id="sess_001",
            turn_number=1,
            tool_name="read_file",
            tool_args={"path": "~/secret.txt"},
            tool_result="data",
            outcome="success",
            latency_ms=10,
        )
        fde_path = tmp_path / "fde" / "sess_001.jsonl"
        record = json.loads(fde_path.read_text(encoding="utf-8"))
        assert record["tool_name"] == "read_file"


class TestFdeCaptureUpload:
    def test_upload_noop_when_no_endpoint(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        # Should not raise — just logs
        capture.try_upload(session_id="sess_001")

    @patch("httpx.Client")
    def test_upload_posts_when_endpoint_set(self, mock_client_cls, tmp_path):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        capture = FdeCapture(enabled=True, data_dir=tmp_path, endpoint="https://fde.example.com/upload")
        capture.capture_tool_call(
            session_id="sess_001",
            turn_number=1,
            tool_name="read_file",
            tool_args={},
            tool_result="ok",
            outcome="success",
            latency_ms=10,
        )
        capture.try_upload(session_id="sess_001")

        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert "fde.example.com" in call_url


class TestFdeCaptureEdgeCases:
    def test_none_args(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        capture.capture_tool_call(
            session_id="sess_001", turn_number=1, tool_name="read_file",
            tool_args=None, tool_result="ok", outcome="success", latency_ms=10,
        )
        fde_path = tmp_path / "fde" / "sess_001.jsonl"
        assert fde_path.exists()

    def test_long_result_truncated(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path, max_result_length=50)
        long_result = "x" * 500
        capture.capture_tool_call(
            session_id="sess_001", turn_number=1, tool_name="read_file",
            tool_args={}, tool_result=long_result, outcome="success", latency_ms=10,
        )
        fde_path = tmp_path / "fde" / "sess_001.jsonl"
        record = json.loads(fde_path.read_text(encoding="utf-8"))
        assert len(record["tool_result"]) <= 50

    def test_directory_created_automatically(self, tmp_path):
        capture = FdeCapture(enabled=True, data_dir=tmp_path)
        assert not (tmp_path / "fde").exists()
        capture.capture_tool_call(
            session_id="sess_001", turn_number=1, tool_name="read_file",
            tool_args={}, tool_result="ok", outcome="success", latency_ms=10,
        )
        assert (tmp_path / "fde").is_dir()
