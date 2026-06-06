"""
Tests for retrieval and injection — T-09 through T-14.

TDD: written FIRST; must fail before implementation.
"""
from __future__ import annotations
import struct
import math
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _make_db(tmp_home):
    from aede.config import bootstrap
    from aede.db import DB

    bootstrap(tmp_home)
    db_path = tmp_home / "data" / "aede.db"
    return DB(db_path)


def _rand_unit_vec(dim: int, seed: int) -> list[float]:
    """Deterministic pseudo-random unit vector."""
    import math
    # Simple LCG
    vals = []
    state = seed
    for _ in range(dim):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        vals.append((state / 0xFFFFFFFF) * 2 - 1)
    mag = math.sqrt(sum(v * v for v in vals))
    return [v / mag for v in vals]


# ---------------------------------------------------------------------------
# T-09: Embedding BLOB round-trip
# ---------------------------------------------------------------------------


def test_learnings_table_exists(tmp_home):
    """The 'learnings' table is created by DB DDL."""
    db = _make_db(tmp_home)
    tables = db.con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='learnings'"
    ).fetchone()
    assert tables is not None, "learnings table not found in DB"
    db.close()


def test_learnings_fts_table_exists(tmp_home):
    """The 'learnings_fts' FTS5 virtual table is created by DB DDL."""
    db = _make_db(tmp_home)
    tables = db.con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='learnings_fts'"
    ).fetchone()
    assert tables is not None, "learnings_fts table not found in DB"
    db.close()


def test_embedding_blob_round_trip(tmp_home):
    """Store a learning with embedding, fetch it, unpack BLOB, cosine > 0.9999."""
    from aede.db import DB
    from aede.config import bootstrap

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    vec = _rand_unit_vec(768, seed=42)
    blob = struct.pack(f"{len(vec)}f", *vec)

    db.insert_learning(
        id="01TEST00000000000000000001",
        type="anti-pattern",
        content="Test learning content",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=blob,
    )

    rows = db.get_all_learnings()
    assert len(rows) == 1, f"Expected 1 learning row, got {len(rows)}"
    row = rows[0]

    raw_blob = row["embedding"]
    assert raw_blob is not None, "embedding BLOB is None after round-trip"

    n = len(raw_blob) // 4
    unpacked = list(struct.unpack(f"{n}f", raw_blob))
    sim = _cosine(vec, unpacked)
    assert sim > 0.9999, f"Cosine similarity {sim} is less than 0.9999"

    db.close()


def test_insert_learning_no_embedding(tmp_home):
    """insert_learning works fine without an embedding (embedding=None)."""
    from aede.db import DB
    from aede.config import bootstrap

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    db.insert_learning(
        id="01TEST00000000000000000002",
        type="root-cause",
        content="No embedding here",
        source="auto_learned",
        trusted=False,
        lower_trust=False,
        verifier_outcome=None,
        embedding=None,
    )

    rows = db.get_all_learnings()
    assert len(rows) == 1
    assert rows[0]["embedding"] is None
    db.close()


def test_store_write_learning_mirrors_to_db(tmp_home):
    """LearningsStore.write_learning with a DB instance mirrors record to DB."""
    from aede.config import bootstrap
    from aede.memory.store import LearningsStore
    from aede.db import DB

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")
    store = LearningsStore(tmp_home / "data", db=db)

    vec = [0.1] * 768
    blob = struct.pack(f"{len(vec)}f", *vec)

    record = store.write_learning(
        type="anti-pattern",
        content="Testing DB mirror",
        source="user",
        source_session_id="S1",
        embedding=blob,
    )

    rows = db.get_all_learnings()
    assert len(rows) == 1, f"Expected 1 DB row, got {len(rows)}"
    assert rows[0]["id"] == record["id"]
    assert rows[0]["content"] == "Testing DB mirror"
    db.close()


# ---------------------------------------------------------------------------
# T-10: top_k_cosine
# ---------------------------------------------------------------------------


def _insert_learning_with_vec(db, i: int, vec: list[float], trusted: bool = True):
    """Helper: insert a learning row with a packed embedding."""
    blob = struct.pack(f"{len(vec)}f", *vec)
    db.insert_learning(
        id=f"01TEST{i:019d}",
        type="anti-pattern",
        content=f"Learning number {i}",
        source="user",
        trusted=trusted,
        lower_trust=False,
        verifier_outcome=None,
        embedding=blob,
    )


def test_top_k_cosine_nearest_ranks_first(tmp_home):
    """Insert 100 learnings; top_k_cosine returns the nearest as rank #1."""
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.retrieval import top_k_cosine

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    # Insert 100 random learnings
    for i in range(100):
        _insert_learning_with_vec(db, i, _rand_unit_vec(768, seed=i))

    # Known query vector = same as learning #42
    query_vec = _rand_unit_vec(768, seed=42)

    results = top_k_cosine(query_vec, db=db, k=5, trusted_only=True)
    assert len(results) > 0, "top_k_cosine returned no results"
    assert results[0]["id"] == f"01TEST{42:019d}", (
        f"Expected learning #42 to rank first, got {results[0]['id']}"
    )
    db.close()


def test_top_k_cosine_trusted_only_filters(tmp_home):
    """trusted_only=True excludes untrusted learnings."""
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.retrieval import top_k_cosine

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    # Insert 5 trusted, 5 untrusted
    for i in range(5):
        _insert_learning_with_vec(db, i, _rand_unit_vec(768, seed=i), trusted=True)
    for i in range(5, 10):
        _insert_learning_with_vec(db, i, _rand_unit_vec(768, seed=i), trusted=False)

    query_vec = _rand_unit_vec(768, seed=0)
    results = top_k_cosine(query_vec, db=db, k=10, trusted_only=True)
    assert all(r["trusted"] for r in results), "Non-trusted learning in trusted_only results"
    db.close()


# ---------------------------------------------------------------------------
# T-11: fts_retrieve
# ---------------------------------------------------------------------------


def test_fts_retrieve_finds_matching_rows(tmp_home):
    """fts_retrieve returns rows matching the keyword."""
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.retrieval import fts_retrieve

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    db.insert_learning(
        id="01FTS00000000000000000001",
        type="anti-pattern",
        content="Never use eval in production code",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=None,
    )
    db.insert_learning(
        id="01FTS00000000000000000002",
        type="root-cause",
        content="Unrelated learning about databases",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=None,
    )

    results = fts_retrieve("eval production", db=db)
    assert len(results) >= 1, "fts_retrieve returned no results for keyword 'eval'"
    ids = [r["id"] for r in results]
    assert "01FTS00000000000000000001" in ids, "Expected the eval learning to be returned"
    db.close()


def test_fts_retrieve_no_match_returns_empty(tmp_home):
    """fts_retrieve returns empty list when no rows match."""
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.retrieval import fts_retrieve

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    db.insert_learning(
        id="01FTS00000000000000000003",
        type="anti-pattern",
        content="Only talks about apples",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=None,
    )

    results = fts_retrieve("xyzzynosuchword", db=db)
    assert results == [], f"Expected empty list, got {results}"
    db.close()


# ---------------------------------------------------------------------------
# T-12: hybrid_retrieve
# ---------------------------------------------------------------------------


def test_hybrid_retrieve_high_signal_ranks_first(tmp_home):
    """An item with both high cosine and FTS match ranks above single-signal items."""
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.retrieval import hybrid_retrieve
    from aede.memory.embeddings import OllamaUnavailable

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    # "Both signals" learning: matches keyword "zebra" AND will be close in cosine
    target_vec = _rand_unit_vec(768, seed=99)
    blob_target = struct.pack(f"{len(target_vec)}f", *target_vec)

    db.insert_learning(
        id="01HYB00000000000000000001",
        type="anti-pattern",
        content="zebra crossing pattern should be avoided",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=blob_target,
    )

    # FTS-only learning: matches keyword but different embedding direction
    orthogonal_vec = _rand_unit_vec(768, seed=1000)
    blob_ortho = struct.pack(f"{len(orthogonal_vec)}f", *orthogonal_vec)

    db.insert_learning(
        id="01HYB00000000000000000002",
        type="root-cause",
        content="zebra is mentioned here but unrelated vector",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=blob_ortho,
    )

    # Cosine-only learning: close embedding but no keyword match
    close_vec = _rand_unit_vec(768, seed=99)  # same seed = identical vector
    blob_close = struct.pack(f"{len(close_vec)}f", *close_vec)
    db.insert_learning(
        id="01HYB00000000000000000003",
        type="config-correction",
        content="completely different topic entirely",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=blob_close,
    )

    # Mock embed_text to return target_vec for the query
    with patch("aede.memory.retrieval._get_ollama_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.embed_text.return_value = target_vec
        mock_get_client.return_value = mock_client

        results = hybrid_retrieve("zebra crossing", db=db, k=3, trusted_only=True)

    assert len(results) > 0, "hybrid_retrieve returned no results"
    # The both-signals item should rank first
    assert results[0]["id"] == "01HYB00000000000000000001", (
        f"Expected both-signals item to rank first, got {results[0]['id']}"
    )
    db.close()


# ---------------------------------------------------------------------------
# T-13: hybrid fallback — Ollama down → FTS only
# ---------------------------------------------------------------------------


def test_hybrid_fallback_on_ollama_down(tmp_home):
    """When Ollama is down, hybrid_retrieve falls back to FTS results without crashing."""
    import aede.memory.retrieval as retrieval_mod
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.retrieval import hybrid_retrieve
    from aede.memory.embeddings import OllamaUnavailable

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    db.insert_learning(
        id="01FALL0000000000000000001",
        type="anti-pattern",
        content="keyword retrieval fallback test content",
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=None,
    )

    # Reset the module-level "warned" flag so warning prints fresh
    retrieval_mod._ollama_warned = False

    with patch("aede.memory.retrieval._get_ollama_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.embed_text.side_effect = OllamaUnavailable("down")
        mock_get_client.return_value = mock_client

        results = hybrid_retrieve("keyword retrieval fallback", db=db, k=5, trusted_only=True)

    # Should return FTS results, not crash
    assert isinstance(results, list), "hybrid_retrieve should return a list"
    ids = [r["id"] for r in results]
    assert "01FALL0000000000000000001" in ids, "FTS fallback should find the keyword match"
    db.close()


# ---------------------------------------------------------------------------
# T-14: build_learnings_suffix
# ---------------------------------------------------------------------------


def test_build_learnings_suffix_formats_markdown(tmp_home):
    """3 trusted learnings → header present, only trusted, within budget."""
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.embeddings import OllamaUnavailable
    import aede.memory.retrieval as retrieval_mod
    from aede.memory.injection import build_learnings_suffix

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    # Insert 3 trusted learnings
    for i in range(1, 4):
        db.insert_learning(
            id=f"01INJ{i:020d}",
            type="anti-pattern",
            content=f"Trusted learning {i}: avoid pattern X{i}",
            source="user",
            trusted=True,
            lower_trust=(i == 3),  # learning 3 has lower_trust=True
            verifier_outcome=None,
            embedding=None,
        )

    # Insert 1 untrusted learning (should NOT appear)
    db.insert_learning(
        id="01INJUNTRUSTED0000000001",
        type="root-cause",
        content="Untrusted learning should not appear",
        source="auto_learned",
        trusted=False,
        lower_trust=False,
        verifier_outcome=None,
        embedding=None,
    )

    retrieval_mod._ollama_warned = False

    with patch("aede.memory.retrieval._get_ollama_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.embed_text.side_effect = OllamaUnavailable("down for test")
        mock_get_client.return_value = mock_client

        suffix = build_learnings_suffix(
            "avoid pattern X",
            db=db,
            max_tokens=2000,
        )

    assert "## Lessons from Prior Runs" in suffix, "Header missing"
    assert "Untrusted learning" not in suffix, "Untrusted learning should not appear"
    # Lower-trust learning should have the LLM-coherence note
    assert "may be imperfect" in suffix, "Lower-trust provenance note missing"
    # Normal trusted learning should have the test provenance note
    assert "verified by test" in suffix, "Verified-by-test provenance note missing"


def test_token_cap_respected(tmp_home):
    """build_learnings_suffix truncates to stay within max_tokens budget."""
    from aede.config import bootstrap
    from aede.db import DB
    from aede.memory.embeddings import OllamaUnavailable
    import aede.memory.retrieval as retrieval_mod
    from aede.memory.injection import build_learnings_suffix

    bootstrap(tmp_home)
    db = DB(tmp_home / "data" / "aede.db")

    # Insert a learning with very long content
    long_content = "A" * 10000
    db.insert_learning(
        id="01TOKN00000000000000001",
        type="anti-pattern",
        content=long_content,
        source="user",
        trusted=True,
        lower_trust=False,
        verifier_outcome=None,
        embedding=None,
    )

    retrieval_mod._ollama_warned = False

    with patch("aede.memory.retrieval._get_ollama_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.embed_text.side_effect = OllamaUnavailable("down")
        mock_get_client.return_value = mock_client

        suffix = build_learnings_suffix(
            "pattern",
            db=db,
            max_tokens=100,
        )

    # ~4 chars/token => 100 tokens = 400 chars max
    assert len(suffix) <= 500, f"Suffix too long: {len(suffix)} chars for 100-token budget"
