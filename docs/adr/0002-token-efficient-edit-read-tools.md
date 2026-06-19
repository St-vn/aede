# ADR 0002 — Token-efficient file tools: native `edit`, partial `read_file`, `glob`

**Status:** Accepted · 2026-06-18

## Context

A token-usage audit of the production SQLite store (`~/.aede/data/aede.db`)
surfaced a structural inefficiency in aede's file-handling tools. Evidence from
the real coding session titled *"Yo i want you to test these"* (deepseek,
90 turns, 120 tool calls):

- **Cumulative billed input: 3,707,928 tokens** for a session whose live
  context peaked at ~129K. The input curve climbed from ~4.5K/turn at turn 40 to
  129K/turn by turn 80 and never recovered.
- **`write_file` regenerated whole files to change a few lines.** `aede/db.py`
  was rewritten twice at 27,069 and 27,072 chars (~6,750 output tokens each),
  then re-billed as input every subsequent turn.
- **`read_file` re-read the same files repeatedly.** 33 read calls across only
  14 distinct files — `AssistantMessage.tsx` 6×, `server.py` 6×,
  `ChatView.tsx` 5×. Read results account for ~111K tokens in this session and
  ~80% of all tool-result tokens database-wide.
- **No `glob` tool exists.** File discovery falls back to `list_dir`
  (depth-limited) or shelling out via `powershell`.

aede currently has only `write_file` (full content) plus a *cosmetic* diff
renderer (`_enrich_edit_args` in `agent.py:392`) that reads the old file and
attaches `old_string`/`new_string` **for UI display only** — the model still
sends the entire file in `args.content`, so the token cost is the full file.

How efficient agents handle this:

| Agent | Edit | Read |
|---|---|---|
| Claude Code | `Edit` = exact string replacement (`old_string`→`new_string`), sends only the changed hunk | targeted partial reads (offset/limit, ~50 lines around target) |
| Aider | edit blocks / diffs | repo map (symbol signatures, elided bodies) — never auto-loads whole files |
| OpenClaw | diff-based | tiered tool-result cap (16K/32K/64K by window) |
| **aede (before)** | full-file `write_file` + fake diff | whole-file `read_file`, repeated, uncapped |

The missing tool set maps 1:1 onto the measured leaks.

## Decision

Add three Claude-Code-parity native tools, replacing the full-file path for edits:

1. **`edit`** — exact-match string replacement: `{path, old_string, new_string, replace_all?}`.
   `old_string` must match uniquely (unless `replace_all`). The model sends only
   the hunk, not the file. `write_file` is retained for genuine new-file creation
   and full rewrites, but the agent is steered to `edit` for modifications.
2. **`read_file` gains `offset`/`limit`** — read a slice, not the whole file
   (Claude Code default ≤2000 lines). Plus **read-result dedup**: when a file is
   re-read unchanged, the older result in context is replaced with a stub.
3. **`glob`** — pattern file discovery (`**/*.tsx`), mtime-sorted, ripgrep/`pathlib`-backed.

Edit uses the same `old_string`/`new_string` shape the ACP path already emits and
that `rewind.py` already reverse-replays — so one diff-renderer and one
reverse-replay code path serve both native and ACP edits, and rewind becomes
lossless by construction.

## Consequences

- **Positive:** Edits cost ~hunk size, not file size — kills the db.py-rewrite
  class of waste. Partial reads + dedup bound the read re-billing that drove 80%
  of tool-result tokens. `glob` removes `list_dir`/shell file-discovery spam.
  Rewind is lossless. One diff path for native + ACP.
- **Negative:** `edit`'s unique-match requirement causes occasional "old_string
  not unique" retries (the model must include surrounding context). This is the
  same tradeoff Claude Code accepts. `write_file` and `edit` coexist — the agent
  prompt must guide tool choice.
- **Follow-up:** NFR targets set in spec (edit cost ≤ 2× hunk size; bounded
  per-session cumulative growth). Aider-style repo map deferred — high effort,
  marginal once these three land. See ADR 0004 for the sequencing constraint
  relative to the per-model context window.
