---
type: doc
tags: [docs, features]
date_updated: 2026-06-14
---

# Context Selection

`select_context(query, sources?, k?)` is a read-only agent tool that pulls relevant context from up to four orthogonal sources in one call, returning a single text block capped at 4 000 tokens.

## When to call

Use it when the auto-injected learnings prefix (`aede/memory/injection.py`) is insufficient, or when you need a non-learnings source. If `read_file` or `search_files` would already answer the question, call those — they are narrower and faster.

## Sources

| Source | Index | Typical latency (p95) | Notes |
|---|---|---|---|
| `learnings` | FTS5 + cosine (`learnings_fts` + embeddings) | ≤ 800 ms up / ≤ 200 ms down | Ollama-down → FTS-only, one-time warning. |
| `sessions` | FTS5 over `messages_fts` | ≤ 50 ms | ±5 context window + bookends per hit. |
| `docs` | FTS5 over `docs/` + `docs-internal/` (`docs_fts`) | ≤ 100 ms warm / ≤ 2 000 ms cold | Lazy build; rebuilds on `(mtime, size)` change. |
| `files` | ripgrep over `project_dir` | ≤ 500 ms | Returns `file:line:content` lines. |

## Parameters

- `query` (required, string) — natural-language search query.
- `sources` (optional, array of enum) — which sources to query. Default: all four.
- `k` (optional, integer 1-20, default 5) — total result count, divided roughly equally across selected sources.

## Example

```
> select_context({"query": "FTS5 unicode61 tokenizer", "k": 5})
```

Output (excerpt):

```
## Source: learnings (2)
[learning] FTS5 needs unicode61 tokenizer
## Source: sessions (1)
--- Result 1 | session: 01HXYZ... ---
  [user] Investigated FTS5 unicode61 tokenizer
## Source: docs (1)
[docs/architecture/retrieval.md] ...FTS5 needs unicode61...
## Source: files (1)
aede/db.py:63:CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
```

## Output cap and approval

- Output is hard-capped at 4 000 tokens (16 000 chars). A truncation marker is appended when the cap is hit.
- The tool is **auto-approved** (no user gate prompt) — read-only, no side effects.
