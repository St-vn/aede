---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Skills System

**Files:** `aede/skills/schema.py` (65 lines), `aede/skills/loader.py` (38 lines)

## Skill definition (SKILL.md)

YAML frontmatter + body in markdown:
```yaml
---
name: test-writer
description: Writes tests for Python code
trigger_phrases: ["test", "pytest"]
allowed_tools: ["read_file", "write_file", "search_files"]
model: claude-sonnet-4-20250514
---
Skill instruction text body...
```

## SkillDef dataclass (`aede/skills/schema.py:11-65`)

Fields: `name`, `description`, `trigger_phrases`, `allowed_tools`, `model`, `body`, `source_path`. Post-init validation requires non-empty `name` and `description`.

`SkillDef.from_file(path)` (`aede/skills/schema.py:27-65`): parses YAML frontmatter (delimited by `---`) from `.md` files. Raises `SkillLoadError` if frontmatter is absent or malformed.

## load_skills() (`aede/skills/loader.py:10-38`)

Scans:
- Global: `~/.aede/skills/` (all `*.md` and `*.skill` files, plus `SKILL.md` in subdirectories)
- Project: `./skills/` (same format)

Project skills shadow globals with same name. Invalid files are skipped with a warning.

## Injection

Skills injected into dynamic system prompt under `## Agent Skills` section (`aede/agent.py:148-151`). Passed to `AgentLoop.initialize()`.

## Import

Skills can be imported from Claude Code via `/import skill <path>` or `aede --import skill --src <path>`. Maps `allowed-tools` → `allowed_tools`, `trigger` → `trigger_phrases`. Fidelity: ~80%.
