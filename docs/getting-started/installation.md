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

## Optional external tools

aede can drive tools that live on your machine but are **not bundled** with aede —
you install them yourself, and aede uses them only if present. Nothing here is
required for core aede; install only what you need.

| Tool | What it adds | How to install |
|------|--------------|----------------|
| **agent-browser** (Vercel) | Render JavaScript pages / SPAs that `fetch_url` can't read (it refuses HTML by design) | Install the `agent-browser` CLI per Vercel's docs, ensure it's on your `PATH` |
| **Python 3.12+** | Required by agent-browser and most external CLIs aede shells out to | Same Python aede already needs (see Prerequisites above) |
| **Docker** | Sandbox boundary for running external CLIs / browsers safely on untrusted pages | Install Docker Desktop (<https://docs.docker.com/get-docker/>) — only needed if you enable sandboxed execution |

> **Note for non-technical users:** these are advanced, opt-in capabilities.
> If a tool isn't installed, aede simply reports it as unavailable rather than
> guessing — it will never silently substitute a different tool. You can ignore
> this whole section unless you specifically want browser/SPA scraping.

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
| `GROQ_API_KEY` | No | Groq API key for Whisper ASR (free tier available) |
| `GOOGLE_API_KEY` | No | Google API key for Chirp 3 ASR |
| `AEDE_HOME` | No | Override home directory (default: `~/.aede`) |
| `EDITOR` | No | Text editor for config editing (default: `notepad.exe` on Windows, `vi` on POSIX) |
