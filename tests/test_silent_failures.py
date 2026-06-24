import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestRouterWriteLearning:
    """_write_learning_tool logs when Verifier raises."""

    def test_verifier_exception_logged(self, tmp_home, caplog):
        from aede.tools.router import _write_learning_tool

        data_dir = tmp_home / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        args = {
            "type": "root-cause",
            "content": "test learning",
            "source": "user",
            "source_session_id": "",
        }

        with patch("aede.memory.verifier.Verifier") as MockVerifier:
            instance = MockVerifier.return_value
            instance.run_llm_verify.side_effect = Exception("LLM down")
            result = _write_learning_tool(args, data_dir=data_dir)

        assert result.startswith("Learning written:")
        assert any(
            "write_learning: verifier failed for" in r.message
            for r in caplog.records
        )


class TestContextDocsFts:
    """_docs_indexer logs when FTS5 query fails."""

    def test_fts5_exception_logged(self, tmp_home, caplog):
        project_dir = tmp_home / "proj"
        (project_dir / "docs").mkdir(parents=True)
        (project_dir / "docs" / "test.md").write_text("hello world")

        call_count = [0]

        def mock_exec(sql, *a):
            call_count[0] += 1
            if "docs_fts MATCH" in str(sql):
                raise Exception("FTS5 broken")
            r = MagicMock()
            r.fetchall.return_value = []
            return r

        mock_con = MagicMock()
        mock_con.execute.side_effect = mock_exec
        mock_db = MagicMock()
        mock_db.con = mock_con

        from aede.tools.context import _docs_indexer
        result = _docs_indexer("hello", k=5, project_dir=project_dir, db=mock_db)

        assert call_count[0] >= 2

        assert result == []
        assert any(
            "docs FTS5 query failed" in r.message for r in caplog.records
        )


class TestAgentsLoader:
    """_scan_dir logs when agent file parsing fails."""

    def test_parse_error_logged(self, tmp_path, caplog):
        from aede.agents.loader import _scan_dir

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir(parents=True)
        agents_dir.joinpath("broken.agent").write_text("bad", encoding="utf-8")

        with patch("aede.agents.schema.AgentDef.from_file") as mock_from_file:
            mock_from_file.side_effect = ValueError("bad format")
            result = _scan_dir(agents_dir)

        assert result == {}
        assert any(
            "Skipping agent file" in r.message for r in caplog.records
        )


class TestAcpManager:
    """ACP session cache errors logged at debug."""

    def test_load_cache_corrupt_logged(self, tmp_path, caplog):
        from aede.acp.manager import AcpManager
        from aede.acp.registry import AgentRegistry
        from aede.acp.credentials import CredentialProvider

        registry = AgentRegistry(config_dir=tmp_path)
        creds = CredentialProvider(home=tmp_path)
        manager = AcpManager(registry=registry, credential_provider=creds)
        manager._registry._path = tmp_path

        cache_file = manager._sessions_cache_path
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("{corrupt json", encoding="utf-8")

        caplog.set_level("DEBUG")
        result = manager._load_saved_session("test-agent")

        assert result is None
        assert any(
            "ACP session cache error" in r.message for r in caplog.records
        )


def _make_db(tmp_home):
    from aede.db import DB
    return DB(tmp_home / "data" / "aede.db")
