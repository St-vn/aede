---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# SettingsModal

**File:** `ui/components/settings/SettingsModal.tsx`

## Purpose

Full-featured settings modal with 10 tabs covering all configuration domains. Triggered from sidebar Settings button or `/settings` slash commands.

## Tab Layout

| Tab | Icon | Component | Purpose |
|---|---|---|---|
| Config | Cog | `ConfigTab` | Core settings (model, shell, compaction, etc.) |
| Models | Key | `ModelsTab` | Manage model presets |
| MCP | Plug | `McpTab` | MCP server management |
| Context | BarChart3 | `ContextTab` | Context window metrics |
| Memory | BrainCircuit | `MemoryTab` | Learning store management |
| Agents | Bot | `AgentsTab` | Agent definitions CRUD |
| Skills | Sparkles | `SkillsTab` | Skill definitions CRUD |
| Keybinds | Keyboard | `KeybindsTab` | Keyboard shortcuts reference |
| Projects | FolderOpen | `ProjectsTab` | Project directories |
| Import | Download | `ImportTab` | Import agents/skills/MCP |

## Implementation

Uses `Dialog` from shadcn/ui with a vertical `Tabs` orientation. The left sidebar shows tab triggers with icons; the right panel scrolls tab content. Accepts `initialTab` prop for direct navigation from slash commands like `/settings:models`.
