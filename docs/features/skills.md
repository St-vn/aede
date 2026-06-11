---
type: doc
tags: [docs, features]
date_updated: 2026-06-10
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

Skills are loaded from two locations:

- **Global** — `~/.aede/skills/` — every `.md` file or `SKILL.md` inside a subdirectory
- **Project** — `./skills/` — same format, shadows globally loaded skills with the same name

Loaded skills are injected into the dynamic portion of the system prompt under the "## Agent Skills" section. The agent is instructed to consider them when performing relevant tasks.

## Managing Skills

- `/skills` — list loaded skills in the REPL
- `/import skill <path>` — import a skill from Claude Code format

## Importing from Other Harnesses

Skills can be imported from Claude Code. The importer maps `allowed-tools` to `allowed_tools` and `trigger` to `trigger_phrases`, and comments out unsupported fields. Fidelity is approximately 80%.
