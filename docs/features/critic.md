---
type: doc
tags: [docs, features]
date_updated: 2026-06-10
---

# Code Critic

The code critic is an asymmetric LLM pass that reviews proposed code for correctness before it's written to disk. It runs before the approval gate for `write_file` and `create_file` calls that contain code-like content.

## How It Works

When the agent writes code, a separate LLM invocation reviews it with a "ruthless code reviewer" persona. The critic identifies:

| Severity | What it flags |
|----------|---------------|
| **HIGH** | Crashes, data loss, wrong output, broken contracts, security holes |
| **MEDIUM** | Logic bugs that produce wrong results in some cases |
| **LOW** | Edge cases and potential issues |

The critic does **not** comment on style, formatting, whitespace, or naming conventions — only correctness. Findings are displayed to the user, who makes the final decision at the approval gate.

## Configuration

Enable the critic in your config:

```yaml
critic_enabled: true
critic_model: claude-sonnet-4-20250514    # optional separate model
critic_api_base_url: ...                   # optional separate provider
```

If `critic_model` is not set, the critic uses the same model as the main agent (with a critic persona prompt). If `critic_api_base_url` is set, the critic uses a different provider.

## Design

The critic is non-fatal — all exceptions return an empty finding list. It uses a separate token tracking role (`critic`) so you can see how much it costs separately from agent turns.
