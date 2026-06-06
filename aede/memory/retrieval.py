"""
Retrieval functions for aede learnings — Phase 2 Memory Phase C.

Provides:
  top_k_cosine  — vector similarity retrieval using packed BLOB embeddings
  fts_retrieve  — BM25 keyword retrieval via FTS5
  hybrid_retrieve — merged cosine + FTS ranking with Ollama-down fallback
"""
from __future__ import annotations

import struct
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aede.db import DB

# Module-level flag: print Ollama-unavailable warning only once per session
_ollama_warned: bool = False


def _get_ollama_client():
    """Return a default OllamaClient instance (lazy import)."""
    from aede.memory.embeddings import OllamaClient  # lazy
    return OllamaClient()


def top_k_cosine(
    query_embedding: list[float],
    db: "DB",
    k: int = 5,
    trusted_only: bool = True,
) -> list[dict[str, Any]]:
    """Return the top-k learnings by cosine similarity to *query_embedding*.

    Loads all candidate learnings from the DB (those that have an embedding
    BLOB), unpacks each BLOB, computes cosine similarity with numpy, and
    returns the top k sorted by descending similarity.

    Args:
        query_embedding: Float list to compare against stored embeddings.
        db: DB instance to load learnings from.
        k: Number of results to return.
        trusted_only: If True, only consider learnings with trusted=1.

    Returns:
        List of learning dicts sorted by descending cosine similarity.
    """
    import numpy as np  # lazy — heavy import

    rows = db.get_all_learnings()

    candidates = []
    for row in rows:
        if trusted_only and not row.get("trusted"):
            continue
        blob = row.get("embedding")
        if blob is None:
            continue
        n = len(blob) // 4
        vec = list(struct.unpack(f"{n}f", blob))
        candidates.append((row, vec))

    if not candidates:
        return []

    q = np.array(query_embedding, dtype=np.float32)
    q_norm = np.linalg.norm(q)
    if q_norm == 0:
        return []
    q = q / q_norm

    scored = []
    for row, vec in candidates:
        v = np.array(vec, dtype=np.float32)
        v_norm = np.linalg.norm(v)
        if v_norm == 0:
            sim = 0.0
        else:
            sim = float(np.dot(q, v / v_norm))
        scored.append((sim, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:k]]


def fts_retrieve(
    query: str,
    db: "DB",
) -> list[dict[str, Any]]:
    """Return learnings matching *query* via FTS5 BM25 ranking.

    Queries the ``learnings_fts`` virtual table using a MATCH expression
    and returns rows ordered by BM25 rank (best first).

    Args:
        query: FTS5 MATCH expression (keyword or phrase).
        db: DB instance to query.

    Returns:
        List of learning dicts ranked by BM25 relevance.
    """
    # Wrap each token in double-quotes to prevent FTS5 syntax interpretation
    # (e.g. operators like "AND"/"OR" causing errors or silent no-match).
    # Skip single-character tokens — SQLite's unicode61 tokenizer ignores them.
    safe_terms = " ".join(
        f'"{t}"' for t in query.split() if len(t.strip()) > 1
    )
    if not safe_terms:
        return []

    try:
        hits = db.con.execute(
            """
            SELECT l.*
            FROM learnings l
            JOIN learnings_fts f ON l.rowid = f.rowid
            WHERE learnings_fts MATCH ?
            ORDER BY rank
            """,
            (safe_terms,),
        ).fetchall()
    except Exception:
        # FTS5 MATCH syntax error or other issue — return empty
        return []
    return list(hits)


def hybrid_retrieve(
    query: str,
    db: "DB",
    k: int = 5,
    trusted_only: bool = True,
    w1: float = 0.5,
    w2: float = 0.5,
) -> list[dict[str, Any]]:
    """Merge FTS5 BM25 and cosine similarity into a hybrid ranking.

    Embeds *query* via Ollama; on OllamaUnavailable, degrades to FTS-only
    (prints a one-time warning).  Merges both result lists with
    ``combined = w1 * norm_fts_rank + w2 * cosine_sim``, deduplicates by id,
    and returns the top k.

    Args:
        query: Natural-language query string.
        db: DB instance.
        k: Number of results to return.
        trusted_only: If True, only include trusted learnings.
        w1: Weight for FTS score (default 0.5).
        w2: Weight for cosine score (default 0.5).

    Returns:
        Ranked list of learning dicts.
    """
    global _ollama_warned

    from aede.memory.embeddings import OllamaUnavailable  # lazy

    # --- Try cosine retrieval ---
    cosine_results: list[dict[str, Any]] = []
    cosine_ids: dict[str, float] = {}  # id -> cosine_sim

    try:
        client = _get_ollama_client()
        query_vec = client.embed_text(query)
        cosine_results = top_k_cosine(query_vec, db=db, k=k * 2, trusted_only=trusted_only)
        if cosine_results:
            # Normalize cosine scores: they're already in [-1, 1]; shift to [0, 1]
            for i, row in enumerate(cosine_results):
                # Rank-based score: 1.0 for #1, decaying
                cosine_ids[row["id"]] = 1.0 - (i / max(len(cosine_results), 1))
    except OllamaUnavailable:
        if not _ollama_warned:
            print("Ollama unavailable — using keyword-only retrieval")
            _ollama_warned = True

    # --- FTS retrieval ---
    fts_results = fts_retrieve(query, db=db)
    if trusted_only:
        fts_results = [r for r in fts_results if r.get("trusted")]

    fts_ids: dict[str, float] = {}
    if fts_results:
        for i, row in enumerate(fts_results):
            fts_ids[row["id"]] = 1.0 - (i / max(len(fts_results), 1))

    # --- If no cosine, return FTS directly ---
    if not cosine_results and not fts_ids:
        return []
    if not cosine_results:
        return fts_results[:k]

    # --- Merge ---
    all_ids: set[str] = set(cosine_ids) | set(fts_ids)
    # Build a lookup for row data
    row_by_id: dict[str, dict[str, Any]] = {}
    for row in cosine_results:
        row_by_id[row["id"]] = row
    for row in fts_results:
        row_by_id[row["id"]] = row

    scored: list[tuple[float, dict[str, Any]]] = []
    for rid in all_ids:
        score = w1 * fts_ids.get(rid, 0.0) + w2 * cosine_ids.get(rid, 0.0)
        if rid in row_by_id:
            scored.append((score, row_by_id[rid]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:k]]
