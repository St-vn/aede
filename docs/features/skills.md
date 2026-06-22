---
type: doc
tags: [docs, features]
date_updated: 2026-06-20
---

# Skills

Skills are reusable instruction templates that get injected into the agent's system prompt. They provide the agent with specialized knowledge and guidelines for particular domains.

## Defining a Skill

Create a `SKILL.md` file in `~/.aede/skills/` (global) or `./skills/` (project):

```yaml
---
name: python-testing
description: Best practices for Python testing
trigger_phrases: ["test", "pytest", "unittest"]
allowed_tools: ["read_file", "write_file", "search_files"]
model: claude-sonnet-4-20250514
---
When writing Python tests:
- Use pytest as the test runner
- Place tests in the `tests/` directory
- Use descriptive test function names
- One assertion per test where possible
```

Available frontmatter fields:

| Field | Default | Description |
|-------|---------|-------------|
| `name` | required | Skill name |
| `description` | required | What this skill does |
| `trigger_phrases` | `[]` | Phrases that suggest this skill should be active |
| `allowed_tools` | `null` | Tool allowlist when this skill is active |
| `model` | `null` | Optional model override |

## How Skills Work

Skills are loaded from three locations, scanned in this order (a later scan replaces an earlier skill with the same name):

1. **Global** — `~/.aede/skills/` — every `.md` file or `SKILL.md` inside a subdirectory
2. **Project** — `./skills/` — same format; this is also where the bundled skills ship (see below)
3. **Claude Code fallback** — `~/.claude/skills/` — skills installed for Claude Code are automatically available in aede

Loaded skills are injected into the dynamic portion of the system prompt under the "## Agent Skills" section. The agent is instructed to consider them when performing relevant tasks.

## Bundled Skills

aede ships with two pre-installed skills in the repo's `skills/` directory. They load automatically when you run aede from the project root and become active when their trigger phrases match the task:

| Skill | What it does |
|-------|-------------|
| `agent-orchestration` | Guides delegation decisions using the orchestrator-worker pattern. Helps the agent decide when to split work across subagents, how to size and scope subagent tasks, which model to assign to each role, and how to coordinate parallel or sequential dispatch. Triggers on phrases like "delegate", "subagent", "parallel", "fan-out", and "decompose". |
| `documents` | Creates, edits, and inspects Office documents and PDFs (`.docx`, `.pdf`, `.pptx`, `.xlsx`). Picks the right library per format, includes code templates and format-specific pitfalls, and runs a visual-QA pass for slides and complex documents. Triggers on phrases like "report", "spreadsheet", "build a deck", "convert to pdf", and "extract tables". |

## Managing Skills

- `/skills` — list loaded skills in the REPL
- `/import skill <path>` — import a skill from Claude Code format

## Importing from Other Harnesses

Skills can be imported from Claude Code. The importer maps `allowed-tools` to `allowed_tools` and `trigger` to `trigger_phrases`, and comments out unsupported fields. Fidelity is approximately 80%.
