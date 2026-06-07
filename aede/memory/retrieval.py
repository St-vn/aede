from __future__ import annotations
import struct
import math
from typing import Any

from aede.memory.embeddings import OllamaUnavailable


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(av * bv for av, bv in zip(a, b))
    na = math.sqrt(sum(av * av for av in a))
    nb = math.sqrt(sum(bv * bv for bv in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _unpack_embedding(learning: dict[str, Any]) -> list[float] | None:
    raw = learning.get("embedding_b64")
    if raw is None:
        return None
    try:
        blob = bytes.fromhex(raw)
        return list(struct.unpack("768f", blob))
    except Exception:
        return None


async def top_k_cosine(
    store: Any,
    query_embedding: list[float],
    k: int = 5,
    trusted_only: bool = True,
) -> list[dict[str, Any]]:
    """Return top-k learnings by cosine similarity to query_embedding."""
    items = store.read_all()
    scored: list[tuple[float, dict]] = []
    for item in items:
        if trusted_only and not item.get("trusted", False):
            continue
        vec = _unpack_embedding(item)
        if vec is None:
            continue
        score = _cosine_similarity(query_embedding, vec)
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, "learning": item} for s, item in scored[:k]]


async def fts_retrieve(
    store: Any,
    query: str,
    k: int = 5,
    trusted_only: bool = True,
) -> list[dict[str, Any]]:
    """Return learnings matching query keywords via FTS5."""
    items = store.read_all()
    query_lower = query.lower()
    scored: list[tuple[int, dict]] = []
    for item in items:
        if trusted_only and not item.get("trusted", False):
            continue
        content = item.get("content", "").lower()
        if query_lower in content:
            scored.append((1, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, "learning": item} for s, item in scored[:k]]


_ollama_warning_printed = False


async def hybrid_retrieve(
    store: Any,
    query: str,
    k: int = 5,
    trusted_only: bool = True,
) -> list[dict[str, Any]]:
    """Combine FTS5 + cosine similarity for ranked retrieval.

    Falls back to FTS5-only when Ollama is unavailable.
    """
    global _ollama_warning_printed

    fts_results = await fts_retrieve(store, query, k * 2, trusted_only)

    try:
        from aede.memory.embeddings import OllamaClient
        client = OllamaClient()
        query_embedding = await client.embed_text(query)
        cosine_results = await top_k_cosine(store, query_embedding, k * 2, trusted_only)
    except OllamaUnavailable:
        if not _ollama_warning_printed:
            import warnings
            warnings.warn("Ollama unavailable — using keyword-only retrieval")
            _ollama_warning_printed = True
        return fts_results[:k]

    merged: dict[str, dict] = {}
    for i, r in enumerate(fts_results):
        lid = r["learning"]["id"]
        merged[lid] = {"score": 0.5 * (1.0 - i / max(len(fts_results), 1)) + 0.5 * 0.0, "learning": r["learning"]}
    for i, r in enumerate(cosine_results):
        lid = r["learning"]["id"]
        if lid in merged:
            merged[lid]["score"] = 0.5 * merged[lid]["score"] + 0.5 * r["score"]
        else:
            merged[lid] = {"score": 0.5 * 0.0 + 0.5 * r["score"], "learning": r["learning"]}

    ranked = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:k]
