'use client'
import React from 'react'
import { Separator } from '@/components/ui/separator'

const IMPORT_COMMANDS = [
  {
    command: '/import agent <path>',
    description: 'Import a Claude Code or OpenCode agent',
    example: '/import agent ~/.claude/agents/my-agent.md',
  },
  {
    command: '/import skill <path>',
    description: 'Import a Claude Code skill (flat .md or SKILL.md dir)',
    example: '/import skill ~/.claude/skills/kaizen',
  },
  {
    command: '/import mcp',
    description: 'Import MCP servers from ~/.claude/mcp.json',
    example: '/import mcp --dry-run',
  },
  {
    command: '/import all',
    description: 'Import everything from ~/.claude/ (agents, skills, MCP)',
    example: '/import all',
  },
]

const SUPPORTED_SOURCES = [
  { source: 'Claude Code', agents: true, skills: true, mcp: true, notes: 'Full support' },
  { source: 'OpenCode', agents: true, skills: false, mcp: false, notes: 'Delegates to Claude Code importer' },
  { source: 'Cursor', agents: false, skills: false, mcp: false, notes: 'Deferred (unstructured format)' },
  { source: 'Windsurf', agents: false, skills: false, mcp: false, notes: 'Deferred (format unknown)' },
]

export function ImportTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium">Import from Other Harnesses</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Import agents, skills, and MCP server configurations from Claude Code or OpenCode.
        </p>
      </div>
      <Separator />

      <div>
        <h4 className="text-xs font-medium mb-2">CLI Commands</h4>
        <div className="space-y-2">
          {IMPORT_COMMANDS.map((cmd, i) => (
            <div key={i} className="rounded-md border border-border p-3 space-y-1">
              <div className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 text-[10px] font-mono rounded border border-border bg-muted shadow-sm">
                  {cmd.command}
                </kbd>
              </div>
              <p className="text-xs text-muted-foreground">{cmd.description}</p>
              <p className="text-[10px] text-muted-foreground font-mono">{cmd.example}</p>
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
          <p>• <strong>Claude Code skills:</strong> Most fields transfer. Only `hidden` is unsupported.</p>
          <p>• <strong>MCP servers:</strong> stdio transport (command+args+env) transfers cleanly. SSE/WebSocket not supported.</p>
        </div>
      </div>
    </div>
  )
}
