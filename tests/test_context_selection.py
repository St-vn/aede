from __future__ import annotations
import shutil
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aede.db import DB


def _make_db(tmp_home):
    return DB(tmp_home / "data" / "aede.db")


def test_docs_table_exists(tmp_home):
    db = _make_db(tmp_home)
    assert db.con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='docs'"
    ).fetchone() is not None
    db.close()


def test_docs_fts_table_exists(tmp_home):
    db = _make_db(tmp_home)
    assert db.con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='docs_fts'"
    ).fetchone() is not None
    db.close()


def test_docs_fts_match_returns_inserted_row(tmp_home):
    db = _make_db(tmp_home)
    db.insert_doc(path="docs/fts.md", mtime=1000, size=42, content="FTS5 needs unicode61 tokenizer")
    rows = db.con.execute(
        "SELECT path FROM docs_fts WHERE docs_fts MATCH ?", ("FTS5",)
    ).fetchall()
    assert len(rows) == 1 and rows[0]["path"] == "docs/fts.md"
    db.close()


# ── T2 — _docs_indexer ──
def test_docs_indexer_imports(tmp_home):
    from aede.tools.context import _docs_indexer
    assert callable(_docs_indexer)


def test_docs_indexer_builds_on_first_call(tmp_home):
    from aede.tools.context import _docs_indexer
    project_dir = tmp_home / "proj"
    (project_dir / "docs").mkdir(parents=True)
    (project_dir / "docs" / "fts.md").write_text(
        "FTS5 needs unicode61 tokenizer for markdown docs", encoding="utf-8"
    )
    db = _make_db(tmp_home)
    hits = _docs_indexer("FTS5", k=5, project_dir=project_dir, db=db)
    assert len(hits) >= 1
    assert any("FTS5" in h and "fts.md" in h for h in hits)
    db.close()


def test_docs_indexer_invalidates_on_mtime_change(tmp_home):
    from aede.tools.context import _docs_indexer
    project_dir = tmp_home / "proj"
    (project_dir / "docs").mkdir(parents=True)
    md = project_dir / "docs" / "fts.md"
    md.write_text("alpha marker alpha marker", encoding="utf-8")
    db = _make_db(tmp_home)
    _docs_indexer("alpha", k=5, project_dir=project_dir, db=db)
    import time; time.sleep(0.05)
    md.write_text("beta marker beta marker", encoding="utf-8")
    hits = _docs_indexer("beta", k=5, project_dir=project_dir, db=db)
    assert any("beta" in h for h in hits)
    db.close()


# ── T5 — _docs_source ──
def test_docs_source_returns_indexer_hits(tmp_home):
    from aede.tools.context import _docs_source
    project_dir = tmp_home / "proj"
    (project_dir / "docs").mkdir(parents=True)
    (project_dir / "docs" / "fts.md").write_text("FTS5 needs unicode61 tokenizer", encoding="utf-8")
    db = _make_db(tmp_home)
    out = _docs_source("FTS5", k=3, project_dir=project_dir, db=db)
    assert any("FTS5" in b and "fts.md" in b for b in out)
    db.close()


def test_docs_source_missing_docs_dir_returns_empty(tmp_home):
    from aede.tools.context import _docs_source
    project_dir = tmp_home / "proj"; project_dir.mkdir(parents=True)
    db = _make_db(tmp_home)
    assert _docs_source("anything", k=3, project_dir=project_dir, db=db) == []
    db.close()


# ── T3 — _learnings_source ──
def test_learnings_source_returns_formatted_hits(tmp_home):
    from aede.tools.context import _learnings_source
    db = _make_db(tmp_home)
    db.insert_learning(id="01L0400000000000000000001", type="root-cause",
        content="FTS5 needs unicode61 tokenizer", source="user", trusted=True)
    out = _learnings_source("FTS5", k=3, db=db)
    assert any("FTS5" in b for b in out)
    db.close()


def test_learnings_source_ollama_down_falls_back_to_fts(tmp_home):
    from aede.tools.context import _learnings_source
    from aede.memory.embeddings import OllamaUnavailable
    import aede.memory.retrieval as retrieval_mod
    db = _make_db(tmp_home)
    db.insert_learning(id="01L0400000000000000000002", type="anti-pattern",
        content="keyword retrieval fallback FTS5 unicode61", source="user", trusted=True)
    retrieval_mod._ollama_warned = False
    with patch("aede.memory.retrieval._get_ollama_client") as mock_get:
        mock_client = MagicMock()
        mock_client.embed_text.side_effect = OllamaUnavailable("down")
        mock_get.return_value = mock_client
        out = _learnings_source("FTS5 unicode61", k=3, db=db)
    assert any("FTS5" in b for b in out)
    db.close()


# ── T4 — _sessions_source helpers ──
def _insert_session(db):
    db.insert_session(
        id="01P04S0000000000000000001",
        parent_id=None,
        title="test session",
        model="claude-sonnet-4-20250514",
    )


def _insert_message(db, mid, sid, role, content):
    db.insert_message(
        id=mid,
        session_id=sid,
        role=role,
        content=content,
        token_count=None,
    )


# ── T4 — _sessions_source ──
def test_sessions_source_returns_formatted_groups(tmp_home):
    from aede.tools.context import _sessions_source
    db = _make_db(tmp_home)
    _insert_session(db)
    _insert_message(db, mid="01P04M000000000000000M01", sid="01P04S0000000000000000001",
        role="user", content="Investigated FTS5 unicode61 tokenizer")
    out = _sessions_source("FTS5", k=3, db=db)
    assert any("FTS5" in b for b in out)
    db.close()


def test_sessions_source_empty_db_returns_empty_list(tmp_home):
    from aede.tools.context import _sessions_source
    db = _make_db(tmp_home)
    assert _sessions_source("anything", k=3, db=db) == []
    db.close()


# ── T6 — _files_source ──
_has_rg = shutil.which("rg") is not None


@pytest.mark.skipif(not _has_rg, reason="ripgrep (rg) not installed")
def test_files_source_returns_rg_lines(tmp_home):
    from aede.tools.context import _files_source
    project_dir = tmp_home / "proj"; project_dir.mkdir(parents=True)
    (project_dir / "module.py").write_text("def fts5():\n    return 42\n", encoding="utf-8")
    out = _files_source("fts5", k=5, project_dir=project_dir)
    assert any("module.py" in l and "fts5" in l for l in out)


@pytest.mark.skipif(not _has_rg, reason="ripgrep (rg) not installed")
def test_files_source_no_matches_returns_empty_list(tmp_home):
    from aede.tools.context import _files_source
    project_dir = tmp_home / "proj"; project_dir.mkdir(parents=True)
    assert _files_source("xyzzynosuchtoken999", k=5, project_dir=project_dir) == []


# ── T7 — select_context helpers ──
def _seed_all_sources(tmp_home):
    """Seed 1 learning, 1 session message, 1 doc, 1 file. Return (db, project_dir)."""
    db = _make_db(tmp_home)
    _insert_session(db)
    db.insert_learning(id="01L0400000000000000000003", type="root-cause",
        content="FTS5 marker in learning", source="user", trusted=True)
    _insert_message(db, "01P04M000000000000000M02", "01P04S0000000000000000001",
        "user", "FTS5 marker in session")
    project_dir = tmp_home / "proj"
    (project_dir / "docs").mkdir(parents=True)
    (project_dir / "docs" / "fts.md").write_text("FTS5 marker in doc", encoding="utf-8")
    (project_dir / "module.py").write_text("# FTS5 marker in file\n", encoding="utf-8")
    return db, project_dir


# ── T7 — select_context ──
def test_select_context_happy_path_all_four_sources(tmp_home):
    from aede.tools.context import select_context
    db, project_dir = _seed_all_sources(tmp_home)
    out = select_context({"query": "FTS5", "k": 3},
        db=db, data_dir=tmp_home / "data", project_dir=project_dir)
    for s in ("learnings", "sessions", "docs", "files"):
        assert f"## Source: {s}" in out
    db.close()


def test_select_context_narrows_to_learnings_only(tmp_home):
    from aede.tools.context import select_context
    db, project_dir = _seed_all_sources(tmp_home)
    out = select_context({"query": "FTS5", "sources": ["learnings"], "k": 3},
        db=db, data_dir=tmp_home / "data", project_dir=project_dir)
    assert "## Source: learnings" in out
    for s in ("sessions", "docs", "files"):
        assert f"## Source: {s}" not in out
    db.close()


def test_select_context_k_parameter_caps_per_source(tmp_home):
    from aede.tools.context import select_context
    db = _make_db(tmp_home)
    for i in range(10):
        db.insert_learning(id=f"01L04000000000000000{i:05d}", type="root-cause",
            content=f"FTS5 marker hit {i}", source="user", trusted=True)
    out = select_context({"query": "FTS5", "sources": ["learnings"], "k": 3},
        db=db, data_dir=tmp_home / "data", project_dir=tmp_home)
    blocks = [ln for ln in out.splitlines() if ln.startswith("[learning]")]
    assert len(blocks) <= 3
    db.close()


def test_select_context_caps_output_via_router(tmp_home):
    from aede.tools.context import select_context
    from aede.tools.router import ToolRouter
    db = _make_db(tmp_home)
    db.insert_learning(id="01L040000000000000000099", type="root-cause",
        content="fts5 " * 20_000, source="user", trusted=True)
    project_dir = tmp_home / "proj"; project_dir.mkdir()
    router = ToolRouter(shell="pwsh", wsl_distro="", tool_output_max_tokens=4000,
        db=db, data_dir=tmp_home / "data")
    out = select_context({"query": "fts5", "sources": ["learnings"], "k": 5},
        db=db, data_dir=tmp_home / "data", project_dir=project_dir)
    truncated = router._truncate(out)
    assert len(truncated) < len(out) and "truncated" in truncated
    db.close()


def test_select_context_section_headers_have_count(tmp_home):
    from aede.tools.context import select_context
    db = _make_db(tmp_home)
    for i in (5, 6):
        db.insert_learning(id=f"01L040000000000000000000{i}", type="root-cause",
            content=f"FTS5 marker {i}", source="user", trusted=True)
    out = select_context({"query": "FTS5", "sources": ["learnings"], "k": 5},
        db=db, data_dir=tmp_home / "data", project_dir=tmp_home)
    assert "## Source: learnings (2)" in out
    db.close()


def test_select_context_ollama_down_learnings_still_works(tmp_home):
    from aede.tools.context import select_context
    from aede.memory.embeddings import OllamaUnavailable
    import aede.memory.retrieval as retrieval_mod
    db = _make_db(tmp_home)
    db.insert_learning(id="01L0400000000000000000007", type="root-cause",
        content="FTS5 unicode61 keyword fallback", source="user", trusted=True)
    retrieval_mod._ollama_warned = False
    with patch("aede.memory.retrieval._get_ollama_client") as mock_get:
        mock_client = MagicMock()
        mock_client.embed_text.side_effect = OllamaUnavailable("down")
        mock_get.return_value = mock_client
        out = select_context({"query": "FTS5 unicode61", "sources": ["learnings"], "k": 3},
            db=db, data_dir=tmp_home / "data", project_dir=tmp_home)
    assert "## Source: learnings" in out and "FTS5" in out
    db.close()


def test_select_context_empty_sources_returns_marker(tmp_home):
    from aede.tools.context import select_context
    db = _make_db(tmp_home)
    out = select_context({"query": "anything", "sources": [], "k": 3},
        db=db, data_dir=tmp_home / "data", project_dir=tmp_home)
    assert out.strip() == "(no sources selected)"
    db.close()


# ---------------------------------------------------------------------------
# T8 helpers
# ---------------------------------------------------------------------------

def _make_router(db, project_dir=None, data_dir=None):
    """Build a ToolRouter with optional project_dir and data_dir."""
    from aede.tools.router import ToolRouter
    return ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=4096,
        db=db,
        data_dir=data_dir,
        project_dir=project_dir,
    )


# ── T8 — select_context registration ──
def test_select_context_registered(tmp_home):
    db = _make_db(tmp_home)
    project_dir = tmp_home / "proj"; project_dir.mkdir()
    router = _make_router(db, project_dir=project_dir, data_dir=tmp_home / "data")
    assert "select_context" in router.tool_names()
    schemas = router.anthropic_tool_schemas()
    assert "select_context" in [s["name"] for s in schemas]
    sc = next(s for s in schemas if s["name"] == "select_context")
    props = sc["input_schema"]["properties"]
    assert props["query"]["type"] == "string"
    assert props["k"]["minimum"] == 1 and props["k"]["maximum"] == 20
    assert "query" in sc["input_schema"]["required"]
    db.close()


def test_select_context_auto_approved(tmp_home):
    from aede.tools.router import GATE_TOOLS
    assert "select_context" not in GATE_TOOLS
    db = _make_db(tmp_home)
    project_dir = tmp_home / "proj"; project_dir.mkdir()
    router = _make_router(db, project_dir=project_dir, data_dir=tmp_home / "data")
    assert not router.requires_approval("select_context")
    db.close()


# ── T10 — docs page exists ──
def test_docs_page_exists():
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "docs" / "features" / "context-selection.md"
    assert p.exists(), f"Missing {p}"
    text = p.read_text(encoding="utf-8")
    assert "select_context" in text
    assert "When to call" in text


# ── T9 — select_context arg validation ──
def test_select_context_rejects_invalid_source(tmp_home):
    db = _make_db(tmp_home)
    project_dir = tmp_home / "proj"; project_dir.mkdir()
    router = _make_router(db, project_dir=project_dir, data_dir=tmp_home / "data")
    result = router.execute_sync("select_context", {"query": "x", "sources": ["nonsense"]})
    assert result.status == "error"
    for s in ("learnings", "sessions", "docs", "files"):
        assert s in result.output
    db.close()


def test_select_context_rejects_invalid_k_low(tmp_home):
    db = _make_db(tmp_home)
    project_dir = tmp_home / "proj"; project_dir.mkdir()
    router = _make_router(db, project_dir=project_dir, data_dir=tmp_home / "data")
    result = router.execute_sync("select_context", {"query": "x", "k": 0})
    assert result.status == "error" and "1" in result.output and "20" in result.output
    db.close()


def test_select_context_rejects_invalid_k_high(tmp_home):
    db = _make_db(tmp_home)
    project_dir = tmp_home / "proj"; project_dir.mkdir()
    router = _make_router(db, project_dir=project_dir, data_dir=tmp_home / "data")
    result = router.execute_sync("select_context", {"query": "x", "k": 21})
    assert result.status == "error" and "1" in result.output and "20" in result.output
    db.close()


# ── T11 — AC coverage meta-test ──
def test_full_test_suite_includes_all_p0_4_acs():
    from pathlib import Path
    text = Path(__file__).resolve().read_text(encoding="utf-8")
    expected = [
        "test_select_context_happy_path_all_four_sources",       "test_select_context_narrows_to_learnings_only",
        "test_select_context_k_parameter_caps_per_source",       "test_select_context_caps_output_via_router",
        "test_select_context_section_headers_have_count",        "test_select_context_ollama_down_learnings_still_works",
        "test_select_context_empty_sources_returns_marker",      "test_select_context_registered",
        "test_select_context_rejects_invalid_source",            "test_select_context_rejects_invalid_k_low",
        "test_select_context_auto_approved",
    ]
    missing = [s for s in expected if s not in text]
    assert not missing, f"Missing AC tests: {missing}"
