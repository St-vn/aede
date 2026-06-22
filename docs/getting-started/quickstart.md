---
type: doc
tags: [docs, getting-started]
date_updated: 2026-06-10
---

# Quickstart

## Start a Session

Launch the REPL:

```bash
uv run aede
```

You'll see a header showing the model and session ID, then a prompt where you can type messages.

Pass a task directly:

```bash
uv run aede "summarize the files in this project"
```

## Your First Conversation

The agent has access to tools for file operations, shell commands, search, and web access. Try:

- "List the files in the current directory"
- "Read the README and tell me what this project does"
- "Search for all TODO comments in the codebase"

When the agent wants to run a shell command or write a file, you'll see an approval prompt:

```
Gate: powershell(cmd="mkdir new_project")
[A]llow once  [S]ession  [P]roject  [G]lobal  [D]eny  [R]edirect
```

Press the corresponding key to respond.

## Slash Commands

Type `/help` to see all available slash commands. Key ones:

| Command | Purpose |
|---------|---------|
| `/help` | List all commands |
| `/resume [id]` | Resume a previous session |
| `/sessions` | List recent sessions |
| `/tokens` | Show token usage and cost |
| `/config [scope] [key] [value]` | View or set configuration |
| `/compact` | Manually trigger context compaction |
| `/clear` | Start a new session |
| `/exit` | End session cleanly |

## End a Session

- `/exit` — archives the session (can be resumed later)
- `Ctrl+C` — saves session as active (resumable)
- `Ctrl+D` — archives the session cleanly

Empty sessions (no messages) are automatically deleted.
