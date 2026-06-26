'use client'
import React from 'react'
import { Separator } from '@/components/ui/separator'

const IMPORT_COMMANDS = [
  {
    command: '/import agent <path> [--source]',
    description: 'Import an agent or rules file (AGENTS.md, GEMINI.md, .cursor/rules/*.mdc)',
    example: '/import agent ~/.codex/AGENTS.md --source codex',
  },
  {
    command: '/import skill <path> [--source]',
    description: 'Import a SKILL.md (flat .md or SKILL.md dir) from any source',
    example: '/import skill ~/.gemini/skills/my-skill --source antigravity',
  },
  {
    command: '/import mcp <path> [--source]',
    description: 'Import MCP servers from a JSON config or Codex config.toml',
    example: '/import mcp --source codex --dry-run',
  },
  {
    command: '/import all [--source]',
    description: "Import everything from a source's standard directories",
    example: '/import all --source windsurf',
  },
]

const SUPPORTED_SOURCES = [
  { source: 'Claude Code', agents: true, skills: true, mcp: true, notes: 'Full support' },
  { source: 'OpenCode', agents: true, skills: false, mcp: false, notes: 'Delegates to Claude Code importer' },
  { source: 'Antigravity', agents: true, skills: true, mcp: true, notes: 'AGENTS.md/GEMINI.md, SKILL.md, JSON MCP' },
  { source: 'Codex', agents: true, skills: true, mcp: true, notes: 'AGENTS.md, SKILL.md, TOML MCP' },
  { source: 'Cursor', agents: true, skills: false, mcp: true, notes: '.mdc rules + JSON MCP (no native skills)' },
  { source: 'Windsurf', agents: true, skills: true, mcp: true, notes: '.windsurf/rules, SKILL.md, JSON MCP' },
]

export function ImportTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium">Import from Other Harnesses</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Import agents, skills, and MCP server configurations from Claude Code, OpenCode,
          Antigravity, Codex, Cursor, and Windsurf.
        </p>
      </div>
      <Separator />

      <div>
        <h4 className="text-xs font-medium mb-2">CLI Commands</h4>
        <div className="space-y-2">
          {IMPORT_COMMANDS.map((cmd, i) => (
            <div key={i} className="rounded-md border border-border p-3 space-y-1">
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 text-xs font-mono rounded border border-border bg-muted shadow-sm">
                  {cmd.command}
                </kbd>
              </div>
              <p className="text-xs text-muted-foreground">{cmd.description}</p>
              <p className="text-xs text-muted-foreground font-mono">{cmd.example}</p>
            </div>
          ))}
        </div>
      </div>
      <Separator />

      <div>
        <h4 className="text-xs font-medium mb-2">Supported Sources</h4>
        <div className="rounded-md border border-border overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left px-3 py-2 font-medium">Source</th>
                <th className="text-center px-2 py-2 font-medium">Agents</th>
                <th className="text-center px-2 py-2 font-medium">Skills</th>
                <th className="text-center px-2 py-2 font-medium">MCP</th>
                <th className="text-left px-3 py-2 font-medium">Notes</th>
              </tr>
            </thead>
            <tbody>
              {SUPPORTED_SOURCES.map((src, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="px-3 py-2 font-medium">{src.source}</td>
                  <td className="text-center px-2 py-2">{src.agents ? '✓' : '—'}</td>
                  <td className="text-center px-2 py-2">{src.skills ? '✓' : '—'}</td>
                  <td className="text-center px-2 py-2">{src.mcp ? '✓' : '—'}</td>
                  <td className="px-3 py-2 text-muted-foreground">{src.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <Separator />

      <div>
        <h4 className="text-xs font-medium mb-2">Fidelity Notes</h4>
        <div className="space-y-1 text-xs text-muted-foreground">
          <p>• <strong>Claude Code agents:</strong> name, description, model transfer. Behavioral fields (hooks, memory, isolation) are commented out.</p>
          <p>• <strong>AGENTS.md / GEMINI.md (Antigravity, Codex, Windsurf):</strong> plain-markdown rules become the agent body; name is synthesized, model defaults to inherit.</p>
          <p>• <strong>Cursor `.mdc` rules:</strong> description + body transfer; `globs` and `alwaysApply` are commented out. Cursor has no native skills.</p>
          <p>• <strong>Skills (SKILL.md):</strong> the cross-tool standard — most fields transfer across all sources.</p>
          <p>• <strong>MCP servers:</strong> stdio (command+args+env) and remote (url) transfer. Codex uses TOML; timeout/OAuth-scope fields are dropped.</p>
        </div>
      </div>
    </div>
  )
}
