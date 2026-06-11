---
type: internal-doc
tags: [docs-internal, design-decisions]
date_updated: 2026-06-10
---

# Rejected Decisions

## Multi-Agent Debate for Critic

Replaced by asymmetric critic. Debate (multiple LLM instances arguing) costs 3-5× more without reliably better outcomes. The current critic is a single LLM pass after each tool execution.

## Agent Import as Separate Entry Points

Early versions had separate `--import-claude-code`, `--import-opencode` CLI flags. Replaced by unified `/import agent|skill|mcp|all` with `--source` parameter for cleaner UX and extensibility.

## YAML-Only MCP Config

Initially assumed all MCP configs would be JSON with `mcpServers` shape. Codex's TOML format forced `import_mcp_from_toml()`. The design now cleanly separates JSON (`_JSON_MCP_SOURCES`) from TOML (Codex-only).

## String Interpolation for Env Vars

`${env:VAR}` and `${file:path}` interpolation in MCP config values was considered but rejected. Env values are passed through verbatim. The user is responsible for resolving references. This avoids complexity and potential security issues with arbitrary file reads.

## No per-Source Converter Registry

Rather than maintaining a registry of converter classes, routing is done via explicit if/elif chains in `_import_one_agent()`. This is simpler for 6 sources and avoids premature abstraction.
