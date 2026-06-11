---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# ModelSelector

**File:** `ui/components/input/ModelSelector.tsx`

## Purpose

Dropdown menu for selecting the active model and configuring reasoning/thinking settings. Rendered inside `InputBar`.

## Model List

Fetches models from `GET /api/models` via `useModels()`. Models are grouped by provider with human-readable labels (`PROVIDER_LABELS` map at line 22-35).

Already selected model shows a checkmark. Selection triggers `onModelChange(id)` and updates server config via `useUpdateConfig`.

## Reasoning Effort

Context-sensitive options per model/provider (`getEffortOptions()`, line 39):
- **Anthropic Opus**: auto/low/medium/high/xhigh/max
- **Anthropic Sonnet**: auto/none
- **OpenAI**: auto/none/minimal/low/medium/high/xhigh
- **DeepSeek**: auto/none/high/max
- **Google/Gemini 2.5**: auto/minimal/low/medium/high
- **OpenRouter**: auto/low/medium/high

## Thinking Budget

Toggle: Off or On (4k budget). Sets `thinking_budget` config value to 0 or 4096.

## Settings Link

"More models..." opens settings modal at the Models tab.
