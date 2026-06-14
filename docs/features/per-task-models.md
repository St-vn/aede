---
type: doc
tags: [docs, features]
date_updated: 2026-06-14
---

# Per-Task Model Selection

Aede lets you assign different models to different tasks within a single session. The orchestrator, subagents, critic, and compaction can each run on a separate model and provider.

## Model Selection Levels

| Task | Config Key | Default | Example Override |
|------|-----------|---------|-----------------|
| Orchestrator | `model` | `claude-sonnet-4-20250514` | `gpt-5.5` |
| Subagent | `model:` in `AGENT.md` frontmatter | inherit from orchestrator | `model: gpt-5.5` |
| Critic | `critic_model` | `null` (same as main) | `claude-haiku-4-20250514` |
| Compaction | `compaction_model` | `null` (use active model) | `deepseek-v4-flash-free` |

## Quick Start

Use a free OpenCode Zen model for the main agent while keeping Claude for compaction:

```yaml
model: deepseek-v4-flash-free
compaction_model: claude-sonnet-4-20250514

providers:
  opencode-zen:
    api_key_env: OPENCODE_ZEN_API_KEY
    base_url: https://opencode.ai/zen/v1
```

Compaction always uses the Anthropic Messages API. When `compaction_model` is set, aede creates a separate Anthropic client for the summarization pass.

## Per-Provider Model Selection

The `providers:` config block routes models to their correct API endpoint and key:

```yaml
providers:
  opencode-zen:
    api_key_env: OPENCODE_ZEN_API_KEY
    base_url: https://opencode.ai/zen/v1
  opencode-go:
    api_key_env: OPENCODE_GO_API_KEY
    base_url: https://opencode.ai/zen/go
```

Zen free models (e.g. `deepseek-v4-flash-free`) and Go models (e.g. `deepseek-v4-pro`) are matched by static ID sets. When the active model matches, aede routes to the corresponding provider automatically.

## Critic with a Separate Provider

The critic can use its own model and API endpoint independently:

```yaml
critic_enabled: true
critic_model: google/gemini-2.5-flash
critic_api_base_url: https://openrouter.ai/api/v1
```

## ACP Agent Routing

ACP agents (codex, claude-code, goose, etc.) have their own model routing via `ACP_MODEL_IDS`. Set the model to an ACP entry and aede routes through the ACP provider instead of a direct LLM API:

```yaml
model: codex/gpt-5.5
model: claude-code/opus-4-8
```

See [ACP](acp.md) for the full list of supported agents and sub-models.
