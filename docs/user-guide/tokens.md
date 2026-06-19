---
type: doc
tags: [docs, user-guide]
date_updated: 2026-06-19
---

# Token Tracking

aede tracks token usage for every turn and provides cost estimation.

## Viewing Usage

In the REPL, use `/tokens` to see:

- Total input, output, and cached tokens
- Separate breakdown for agent vs critic turns
- KV-cache hit rate
- Estimated USD cost

## Cost Estimation

Costs are calculated using a price table. For Anthropic models, built-in fallback prices are used when OpenRouter pricing data is unavailable. The system handles cached vs uncached input billing separately.

## Token Limits

The context window defaults to 200,000 tokens. When usage reaches 85% of this limit, automatic context compaction triggers (see [Architecture: Agent Loop](../architecture/agent-loop.md)). You can also trigger compaction manually with `/compact`.

Configure these in your config:

| Key | Default | Description |
|-----|---------|-------------|
| `context_window` | 200000 | Token limit before compaction triggers |
| `compaction_threshold` | 0.85 | Fraction of window that triggers auto-compaction |

> **Note on the numbers.** Per-turn usage records the *full context resent each
> turn*, so summing turns gives a **cumulative billed** figure that grows with
> turn count and tool-call depth — it is not your live context size. A long
> tool-heavy session can show millions of cumulative tokens while live context
> stays well under the window.

## Coming soon

A per-source context breakdown (how much of your context is system prompt,
instructions, skills, MCP tool schemas, and conversation — raw and %) in the
settings **Context** tab, plus a Compact button and compaction marker in the
context bar above the chatbox. The fixed 200K window will become a per-model
value. See the project roadmap for status.
