---
type: doc
tags: [docs, getting-started]
date_updated: 2026-06-10
---

# Installation

## Prerequisites

- **Python 3.12+** — aede uses modern Python features and the latest SDKs
- **uv** — the Python package manager. Install from <https://docs.astral.sh/uv/>

## Install

Install from PyPI:

```bash
uv tool install aedeai
```

Or run directly without installing:

```bash
uvx aedeai
```

For development, clone the repository and use `uv sync`:

```bash
git clone <repo-url>
cd aede
uv sync
uv run aede
```

## First Run

On first launch, aede creates its home directory at `~/.aede/` with this structure:

```
~/.aede/
├── config.yml          # global user configuration
├── credentials.json    # credential vault (API keys)
├── data/
│   ├── aede.db         # SQLite database
│   ├── learnings.jsonl # learnings store
│   ├── sessions/       # per-session rollout logs
│   └── traces/         # GEPA trace logs
├── skills/             # global skills
└── agents/             # global agents
```

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes (Anthropic) | Anthropic API key for Claude models |
| `OPENROUTER_API_KEY` | OpenRouter | OpenRouter API key |
| `OPENAI_API_KEY` | OpenAI | OpenAI API key |
| `DEEPSEEK_API_KEY` | DeepSeek | DeepSeek API key |
| `AEDE_HOME` | No | Override home directory (default: `~/.aede`) |
| `EDITOR` | No | Text editor for config editing (default: `notepad.exe` on Windows, `vi` on POSIX) |
