---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# SlashCommandPicker

**File:** `ui/components/input/SlashCommandPicker.tsx`

## Purpose

Autocomplete popover for `/` commands. Triggered when user types `/` at position 0 in InputBar.

## Static Commands

15 built-in commands across categories:
- **Session**: `/sessions`, `/compact`, `/clear`, `/resume`
- **Discovery**: `/skills`, `/agents`, `/tools`, `/tokens`, `/mcp`, `/help`
- **Config**: `/config`, `/settings`, `/settings:{tab}` (one per settings tab)

## Dynamic Commands

Built at runtime from server state:
- **Skills**: `/skill {name}` for each registered skill
- **Agents**: `/agent {name}` for each registered agent
- **MCP**: `/mcp {name}` for each enabled MCP server (with tool count)

## Selection Behavior

- `/settings` — opens settings modal
- `/settings:{tab}` — opens settings modal at specific tab
- `/help` — shows help
- All others — inserts the command text into the input

## Implementation

Uses `cmdk` (`Command` component) inside a `Popover`. Commands are memoized with `useMemo` based on skills, agents, and MCP servers data. Filtered case-insensitively by trigger or description. Grouped by category with category-specific icons.
