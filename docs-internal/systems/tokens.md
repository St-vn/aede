---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Token Tracking & Cost Estimation

**File:** `aede/tokens.py` (188 lines)

## TokenTracker class (`aede/tokens.py:59-133`)

Accumulates per-turn token usage in memory, persists each row to the `token_usage` DB table.

| Method | Description |
|--------|-------------|
| `record(turn, input_tokens, output_tokens, cached_tokens, role)` | Append usage row. `role` = `"agent"` \| `"critic"`. Persists via `db.insert_token_usage()`. |
| `totals()` | Returns `{input_tokens, output_tokens, cached_tokens}` |
| `totals_by_role()` | Per-role breakdown |
| `cache_hit_rate()` | `cached_tokens / (input_tokens + cached_tokens)` |

## PriceCache class (`aede/tokens.py:135-188`)

24-hour TTL disk cache for OpenRouter pricing:

- `load()` — reads from JSON file; returns `None` if stale or missing
- `save()` — persists with `fetched_at` timestamp
- `fetch_openrouter()` — async HTTPX call to `openrouter.ai/api/v1/models`, converts per-token prices to per-million-token values (`aede/tokens.py:164-188`)

## estimate_cost() (`aede/tokens.py:24-56`)

Computes USD cost: `(uncached_input / 1M * input_price) + (cached_tokens / 1M * cache_read_price) + (output_tokens / 1M * output_price)`. `FALLBACK_PRICES` dict covers Claude Sonnet 4, Opus 4, Haiku 4 (`aede/tokens.py:15-19`).
