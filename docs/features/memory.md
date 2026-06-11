---
type: doc
tags: [docs, features]
date_updated: 2026-06-10
---

# Memory

The memory system lets aede persist and retrieve learnings across sessions, so knowledge from one conversation carries forward to future ones.

## Learnings Store

Learnings are stored in `~/.aede/data/learnings.jsonl` (append-only JSONL) and mirrored to the SQLite `learnings` table for querying.

Each learning has:

| Field | Description |
|-------|-------------|
| `type` | Category: `anti-pattern`, `failed-approach`, `root-cause`, `config-correction` |
| `content` | Free-text body of the learning |
| `source` | Origin: `user`, `auto_learned`, `test_failure`, `tool_error` |
| `trusted` | Set by verifier after confirmation |
| `embedding` | Vector embedding for similarity search |

## Retrieval

When starting a new turn, aede retrieves relevant learnings using hybrid search:

1. **Cosine similarity** — unpacks stored embeddings and computes similarity
2. **FTS5 full-text search** — SQLite BM25-ranked keyword search
3. **Rank-based merge** — combines both results (default 50/50 weight)

The top learnings are injected into the system prompt under "Lessons from Prior Runs," with provenance notes (e.g., "verified by test" vs "verified by LLM coherence").

## Writing Learnings

Learnings can be written by:

- The agent via the `write_learning` tool (requires approval)
- Using the CLI directly: `aede memory list` / `show` / `delete` / `edit`
- Automatic extraction from sessions via `/extract`

## Verifier

The verifier validates learnings before they're trusted:

- **Code verifier** — runs `uv run pytest` on code-related learnings; marks `trusted=True` on pass
- **LLM verifier** — runs a separate Anthropic coherence check for non-code learnings; marks `lower_trust=True`

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `ollama_base_url` | `http://localhost:11434` | Ollama endpoint for embeddings |
| `ollama_embed_model` | `nomic-embed-text` | Embedding model |
| `learnings_top_k` | 5 | Top-k learnings to retrieve |
| `learnings_max_tokens` | 2000 | Max tokens for learnings suffix |
