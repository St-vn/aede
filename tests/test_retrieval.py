import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import struct
import math


@pytest.mark.asyncio
async def test_top_k_cosine_ranks_nearest(tmp_path):
    """top_k_cosine ranks the most similar embedding #1."""
    from aede.memory.retrieval import top_k_cosine
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")

    target_vec = [float(i) / 768.0 for i in range(768)]

    for i in range(100):
        noise = (99 - i) * 0.0001
        vec = [v + (noise if j == 0 else 0.0) for j, v in enumerate(target_vec)]
        store.write_learning(
            type=LearningType.ANTI_PATTERN,
            content=f"Learning {i}",
            source=LearningSource.USER,
            source_session_id="s1",
            embedding=struct.pack("768f", *vec),
        )

    query_vec = target_vec  # Learning 99 has smallest noise → closest
    results = await top_k_cosine(store=store, query_embedding=query_vec, k=5, trusted_only=False)

    assert len(results) == 5
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0]["learning"]["content"] == "Learning 99"


@pytest.mark.asyncio
async def test_fts_retrieve_keywords(tmp_path):
    """fts_retrieve finds learnings by keyword match."""
    from aede.memory.retrieval import fts_retrieve
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "Never use eval() on user input", LearningSource.USER, "s1")
    store.write_learning(LearningType.ROOT_CAUSE, "Use pathlib instead of os.path", LearningSource.AUTO_LEARNED, "s2")

    results = await fts_retrieve(store=store, query="eval", trusted_only=False)
    assert len(results) >= 1
    assert "eval" in results[0]["learning"]["content"]


@pytest.mark.asyncio
async def test_hybrid_retrieve_combines_signals(tmp_path):
    """hybrid_retrieve combines FTS5 + cosine results."""
    from aede.memory.retrieval import hybrid_retrieve
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "No bare except clauses", LearningSource.USER, "s1")

    results = await hybrid_retrieve(store=store, query="bare except", k=5, trusted_only=False)
    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_hybrid_fallback_to_fts5_when_ollama_down(tmp_path):
    """When Ollama is down, hybrid_retrieve falls back to FTS5-only."""
    from aede.memory.retrieval import hybrid_retrieve
    from aede.memory.store import LearningsStore, LearningType, LearningSource
    from aede.memory.embeddings import OllamaUnavailable

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "No bare except clauses", LearningSource.USER, "s1")

    with patch("aede.memory.embeddings.OllamaClient.embed_text", side_effect=OllamaUnavailable("Ollama down")):
        results = await hybrid_retrieve(store=store, query="bare except", k=5, trusted_only=False)

    assert len(results) >= 1
    assert "bare except" in results[0]["learning"]["content"]
