'use client'
import React, { useMemo } from 'react'
import { Command, CommandGroup, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent } from '@/components/ui/popover'
import { Terminal, Cog, Compass, HelpCircle, Ban, FlaskConical, Puzzle } from 'lucide-react'

interface SlashCommand {
  trigger: string
  description: string
  category: 'session' | 'discovery' | 'config' | 'skills' | 'mcp'
  disabled?: boolean
}

const ALL_COMMANDS: SlashCommand[] = [
  { trigger: '/sessions', description: 'List and switch between sessions', category: 'session' },
  { trigger: '/compact', description: 'Compact session history', category: 'session' },
  { trigger: '/clear', description: 'Clear the current conversation', category: 'session' },
  { trigger: '/resume', description: 'Resume a previous session', category: 'session' },
  { trigger: '/skills', description: 'List available skills', category: 'discovery' },
  { trigger: '/agents', description: 'List available agents', category: 'discovery' },
  { trigger: '/tools', description: 'List available tools', category: 'discovery' },
  { trigger: '/tokens', description: 'View token budget and usage', category: 'discovery' },
  { trigger: '/help', description: 'Show help and all available commands', category: 'discovery' },
  { trigger: '/config', description: 'View and edit configuration', category: 'config' },
  { trigger: '/skills run', description: 'Run a skill — coming soon', category: 'skills', disabled: true },
  { trigger: '/mcp', description: 'List and use MCP tools — coming soon', category: 'mcp', disabled: true },
]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (command: string) => void
  searchQuery: string
  triggerRef: React.RefObject<HTMLElement | null>
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  session: <Terminal className="w-3.5 h-3.5" />,
  discovery: <Compass className="w-3.5 h-3.5" />,
  config: <Cog className="w-3.5 h-3.5" />,
  skills: <FlaskConical className="w-3.5 h-3.5" />,
  mcp: <Puzzle className="w-3.5 h-3.5" />,
}

const CATEGORY_LABELS: Record<string, string> = {
  session: 'Session',
  discovery: 'Discovery',
  config: 'Config',
  skills: 'Skills',
  mcp: 'MCP Tools',
}

export function SlashCommandPicker({ open, onOpenChange, onSelect, searchQuery, triggerRef }: Props) {
  const filtered = useMemo(() => {
    if (!searchQuery) return ALL_COMMANDS
    const q = searchQuery.toLowerCase()
    return ALL_COMMANDS.filter(
      cmd => cmd.trigger.toLowerCase().includes(q) || cmd.description.toLowerCase().includes(q)
    )
  }, [searchQuery])

  const grouped = useMemo(() => {
    const groups: Record<string, SlashCommand[]> = {}
    for (const cmd of filtered) {
      if (!groups[cmd.category]) groups[cmd.category] = []
      groups[cmd.category].push(cmd)
    }
    return groups
  }, [filtered])

  const hasResults = filtered.length > 0

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverContent
        className="w-[300px] p-0 bg-popover text-popover-foreground border border-border shadow-md rounded-lg z-50"
        align="start"
        side="top"
        sideOffset={8}
        initialFocus={false}
        anchor={triggerRef}
      >
        {searchQuery && (
          <div className="px-3 py-1.5 text-[11px] text-muted-foreground/50 border-b border-border font-mono">
            /{searchQuery}
          </div>
        )}
        <Command className="bg-transparent" shouldFilter={false}>
          <CommandList className="max-h-[280px] overflow-y-auto p-1">
            {!hasResults ? (
              <div className="py-6 px-4 text-center text-xs text-muted-foreground">
                No matching commands
              </div>
            ) : (
              Object.entries(grouped).map(([category, cmds]) => (
                <CommandGroup key={category} heading={CATEGORY_LABELS[category] ?? category}>
                  {cmds.map(cmd => (
                    <CommandItem
                      key={cmd.trigger}
                      value={cmd.trigger}
                      disabled={cmd.disabled}
                      onSelect={() => {
                        if (!cmd.disabled) onSelect(cmd.trigger)
                      }}
                      className={`flex items-center gap-2 px-3 py-1.5 text-xs rounded-sm
                        ${cmd.disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer hover:bg-accent hover:text-accent-foreground'}`}
                    >
                      <span className="text-muted-foreground shrink-0">
                        {CATEGORY_ICONS[category]}
                      </span>
                      <span className="font-mono">{cmd.trigger}</span>
                      <span className="flex-1 truncate text-muted-foreground">{cmd.description}</span>
                      {cmd.disabled && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground shrink-0">
                          coming soon
                        </span>
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              ))
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
