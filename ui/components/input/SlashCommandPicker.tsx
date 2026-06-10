'use client'
import React, { useMemo } from 'react'
import { Command, CommandGroup, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent } from '@/components/ui/popover'
import { Terminal, Cog, Compass, FlaskConical, Plug } from 'lucide-react'
import { useSkills, SkillInfo } from '@/hooks/useSkills'
import { useAgents, AgentInfo } from '@/hooks/useAgents'
import { useMcpServers, McpServerInfo } from '@/hooks/useMcpServers'

interface SlashCommand {
  trigger: string
  description: string
  category: 'session' | 'discovery' | 'config' | 'skills' | 'mcp' | 'agents'
}

const STATIC_COMMANDS: SlashCommand[] = [
  { trigger: '/sessions', description: 'List and switch between sessions', category: 'session' },
  { trigger: '/compact', description: 'Compact session history', category: 'session' },
  { trigger: '/clear', description: 'Clear the current conversation', category: 'session' },
  { trigger: '/resume', description: 'Resume a previous session', category: 'session' },
  { trigger: '/skills', description: 'List available skills', category: 'discovery' },
  { trigger: '/agents', description: 'List available agents', category: 'discovery' },
  { trigger: '/tools', description: 'List available tools', category: 'discovery' },
  { trigger: '/tokens', description: 'View token budget and usage', category: 'discovery' },
  { trigger: '/mcp', description: 'List MCP servers and tools', category: 'discovery' },
  { trigger: '/help', description: 'Show help and all available commands', category: 'discovery' },
  { trigger: '/config', description: 'View and edit configuration', category: 'config' },
  { trigger: '/settings', description: 'Open settings modal', category: 'config' },
  { trigger: '/settings:config', description: 'Open settings → Config tab', category: 'config' },
  { trigger: '/settings:models', description: 'Open settings → Models tab', category: 'config' },
  { trigger: '/settings:mcp', description: 'Open settings → MCP tab', category: 'config' },
  { trigger: '/settings:context', description: 'Open settings → Context tab', category: 'config' },
  { trigger: '/settings:memory', description: 'Open settings → Memory tab', category: 'config' },
  { trigger: '/settings:agents', description: 'Open settings → Agents tab', category: 'config' },
  { trigger: '/settings:skills', description: 'Open settings → Skills tab', category: 'config' },
  { trigger: '/settings:keybinds', description: 'Open settings → Keybinds tab', category: 'config' },
  { trigger: '/settings:projects', description: 'Open settings → Projects tab', category: 'config' },
  { trigger: '/settings:import', description: 'Open settings → Import tab', category: 'config' },
]

function buildDynamicCommands(
  skills: SkillInfo[] | undefined,
  agents: AgentInfo[] | undefined,
  mcpServers: Record<string, McpServerInfo> | undefined,
): SlashCommand[] {
  const cmds: SlashCommand[] = []

  if (skills) {
    for (const s of skills) {
      cmds.push({
        trigger: `/skill ${s.name}`,
        description: s.description.slice(0, 60),
        category: 'skills',
      })
    }
  }

  if (agents) {
    for (const a of agents) {
      cmds.push({
        trigger: `/agent ${a.name}`,
        description: a.description.slice(0, 60),
        category: 'agents',
      })
    }
  }

  if (mcpServers) {
    for (const [name, srv] of Object.entries(mcpServers)) {
      if (srv.enabled === false) continue
      const toolCount = srv.tools?.length ?? 0
      const label = toolCount > 0 ? `${toolCount} tools` : srv.command || 'configured'
      cmds.push({
        trigger: `/mcp ${name}`,
        description: `${label} — ${srv.trusted ? 'trusted' : 'gated'}`,
        category: 'mcp',
      })
    }
  }

  return cmds
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (command: string) => void
  searchQuery: string
  triggerRef: React.RefObject<HTMLElement | null>
}

export function SlashCommandPicker({ open, onOpenChange, onSelect, searchQuery, triggerRef }: Props) {
  const { data: skills } = useSkills()
  const { data: agents } = useAgents()
  const { data: mcpServers } = useMcpServers()

  const allCommands = useMemo(() => {
    const dynamic = buildDynamicCommands(skills, agents, mcpServers)
    return [...STATIC_COMMANDS, ...dynamic]
  }, [skills, agents, mcpServers])

  const filtered = useMemo(() => {
    if (!searchQuery) return allCommands
    const q = searchQuery.toLowerCase()
    return allCommands.filter(
      cmd => cmd.trigger.toLowerCase().includes(q) || cmd.description.toLowerCase().includes(q)
    )
  }, [searchQuery, allCommands])

  const grouped = useMemo(() => {
    const groups: Record<string, SlashCommand[]> = {}
    for (const cmd of filtered) {
      if (!groups[cmd.category]) groups[cmd.category] = []
      groups[cmd.category].push(cmd)
    }
    return groups
  }, [filtered])

  const hasResults = filtered.length > 0

  const categoryLabels: Record<string, string> = {
    session: 'Session',
    discovery: 'Discovery',
    config: 'Config',
    skills: 'Skills',
    agents: 'Agents',
    mcp: 'MCP Servers',
  }

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverContent
        className="w-[320px] p-0 bg-popover text-popover-foreground border border-border shadow-md rounded-lg z-50"
        align="start"
        side="top"
        sideOffset={8}
        initialFocus={false}
        anchor={triggerRef}
      >
        {!hasResults ? (
          <div className="py-6 px-4 text-center text-xs text-muted-foreground">
            No matching commands
          </div>
        ) : (
          <Command className="bg-transparent">
            <CommandList className="max-h-[220px] overflow-y-auto p-1">
              {Object.entries(grouped).map(([category, cmds]) => (
                <CommandGroup key={category} heading={categoryLabels[category] || category}>
                  {cmds.map(cmd => (
                    <CommandItem
                      key={cmd.trigger}
                      value={cmd.trigger}
                      onSelect={() => onSelect(cmd.trigger)}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-sm cursor-pointer hover:bg-accent hover:text-accent-foreground"
                    >
                      {category === 'session' ? (
                        <Terminal className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      ) : category === 'discovery' ? (
                        <Compass className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      ) : category === 'config' ? (
                        <Cog className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      ) : category === 'skills' ? (
                        <FlaskConical className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      ) : category === 'agents' ? (
                        <FlaskConical className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      ) : (
                        <Plug className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      )}
                      <span className="font-mono">{cmd.trigger}</span>
                      <span className="flex-1 truncate text-muted-foreground">{cmd.description}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              ))}
            </CommandList>
          </Command>
        )}
      </PopoverContent>
    </Popover>
  )
}
