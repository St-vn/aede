---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Model Presets

**File:** `aede/models.py` (90 lines)

## MODEL_PRESETS (`aede/models.py:7-56`)

Hardcoded dictionary of provider → model list:

| Provider | Models |
|----------|--------|
| `anthropic` | Claude Fable 5, Claude Opus 4.8, Claude Sonnet 4.6 |
| `openai` | GPT-5.5 |
| `deepseek` | DeepSeek Chat (V4) |
| `openrouter` | OpenRouter Auto |
| `google-ai` | Gemini 3.5 Flash |
| `codex` | Codex, Codex/GPT-5.5, Codex/o3, Codex/o4-mini |
| `claude-code` | Claude Code, sub-entries for Fable 5/Opus 4.8/Sonnet 4.6/Haiku 4.5 |
| `gemini` | Gemini |
| `agy` | Antigravity, sub-entries for Gemini/Claude models |
| `cline` | Cline |
| `cursor` | Cursor |
| `goose` | Goose, sub-entries for Claude Sonnet 4.6/GPT-4o |
| `opencode` | OpenCode |

## Load/Save/Reset

- `load_models(home)` — reads from `~/.aede/models.json`; falls back to `default_models()` on missing/corrupt file (`aede/models.py:71-78`)
- `save_models(home, models)` — writes to `models.json` (`aede/models.py:81-84`)
- `reset_models(home)` — deletes the file to restore factory defaults (`aede/models.py:87-89`)
- `default_models()` — flattens `MODEL_PRESETS` into `[{id, label, provider}]` list (`aede/models.py:63-68`)

## ACP Model IDs (`aede/provider.py:523-533`)

`ACP_MODEL_IDS` frozenset defines which model names route through ACP rather than LLM API. Includes base agent names and sub-model entries (e.g. `claude-code/opus-4-8`, `codex/gpt-5.5`).
