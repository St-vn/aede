---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Memory System

**Files:** `aede/memory/` — Phase 2 feature

## LearningsStore (`aede/memory/store.py`, 202 lines)

Append-only JSONL store at `~/.aede/data/learnings.jsonl`. Each learning is a JSON object on its own line.

**Schema:**
- `type`: `anti-pattern` | `failed-approach` | `root-cause` | `config-correction`
- `source`: `user` | `auto_learned` | `test_failure` | `tool_error`
- `trusted` / `lower_trust` / `verifier_outcome` — lifecycle fields managed by verifier
- `embedding` — packed BLOB for cosine similarity
- `provenance`, `importance_count`, `conflicting_rule_ids` — extraction metadata

**Methods:** `write_learning()` (validates + appends), `list_all()` (reads entire file), `get()` (by id), `delete()` (full rewrite), `update()` (full rewrite). Optionally mirrors to DB learnings table when `db` argument provided.

## Ollama Embeddings (`aede/memory/embeddings.py`, 63 lines)

`OllamaClient.embed_text(text)` → POST to `{base_url}/api/embeddings`. Default model: `nomic-embed-text` (768 dims). Timeout: 5 seconds. Raises `OllamaUnavailable` on connection errors (caught by callers for graceful degradation).

## Retrieval (`aede/memory/retrieval.py`, 208 lines)

Three strategies:
1. **top_k_cosine()** — unpacks BLOB embeddings via `struct.unpack`, computes cosine similarity with numpy, returns top-k trusted learnings
2. **fts_retrieve()** — BM25 ranking via FTS5 `learnings_fts` virtual table. Wraps terms in double-quotes to prevent FTS5 syntax interpretation, skips single-char tokens
3. **hybrid_retrieve()** — rank-based merge (default 0.5/0.5 weights), dedup by ID. Degrades to FTS-only when Ollama unavailable (one-time warning via `_ollama_warned` module flag)

## System Prompt Injection (`aede/memory/injection.py`, 72 lines)

`build_learnings_suffix(task_description, db)` calls `hybrid_retrieve()` → formats as `## Lessons from Prior Runs` markdown block → truncates to fit token budget (default 2000 tokens). Each entry includes provenance: "verified by test" vs "verified by LLM coherence (may be imperfect)".

## Verifier (`aede/memory/verifier.py`, 161 lines)

Pure verdict functions — never write to store, return update dicts:
- **run_code_verify()** — runs `uv run pytest` via subprocess (injectable runner). Returns `trusted=True` on pass
- **run_llm_verify()** — separate Anthropic coherence check via `claude-haiku-4-5`. Never sets `trusted=True` — non-code learnings are always `lower_trust=True` (locked decision Q5)

## TraceExtractor (`aede/memory/extractor.py`, 563 lines)

Post-task pass that mines completed rollout traces for typed learnings:
1. `normalize_rollout()` — pairs tool_call/tool_result records by call_id, assigns GEPA scores (1.0/0.5/0.0)
2. `should_extract()` — trigger gate: ≥5 tool calls + ≥1 non-transient failure→fix loop
3. `TraceExtractor.extract()` — LLM extraction via `claude-haiku-4-5`, produces critique-then-fix records
4. `gate_candidate()` — confidence gate (≥0.6), non-triviality gate, admissibility gate, write to store, verifier gate

**ExtractionQueue** (`aede/memory/extractor.py:432-563`): deferred post-session markers. Enqueues at session end, processes on next startup to avoid racing DB teardown.

## Admissibility (`aede/memory/admissibility.py`, 107 lines)

Meta-Policy Reflexion: LLM check whether a candidate prescriptive rule contradicts any existing trusted rule. Returns `AdmissibilityResult(admissible, conflicting_rule_ids, reason)`.
