'use client'
import React from 'react'
import { Check, Scroll, Pause, FileCode, Rocket, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const MODES = [
  { value: 'plan', label: 'Plan mode', description: 'Read-only. Writes and shell denied.', icon: Scroll },
  { value: 'normal', label: 'Ask before edits', description: 'Read auto, writes/shell gated.', icon: Pause },
  { value: 'allow_write_read', label: 'Edit automatically', description: 'Read + Write files auto, shell gated.', icon: FileCode },
  { value: 'execution', label: 'Execute', description: 'Auto-approve with safety-net.', icon: Rocket },
  { value: 'auto', label: 'Danger Zone', description: 'No filter. No questions. Hands-free.', icon: TriangleAlert },
]

interface Props {
  currentMode: string
  onModeChange: (mode: string) => void
}

export function ModeSelector({ currentMode, onModeChange }: Props) {
  const current = MODES.find(m => m.value === currentMode) ?? MODES[1]
  const CurrentIcon = current.icon

  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={
        <Button variant="ghost" size="sm" aria-label="Select permission mode"
          className="text-xs text-muted-foreground gap-1 max-w-[120px] truncate">
          <CurrentIcon className="w-3 h-3 shrink-0" />
          {current.label}
        </Button>
      } />
      <DropdownMenuContent align="end" className="min-w-[220px]">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Permission Mode
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        {MODES.map(m => {
          const Icon = m.icon
          return (
            <DropdownMenuItem key={m.value} onClick={() => onModeChange(m.value)}
              className="text-xs flex items-start gap-2 py-2">
              <Icon className="w-4 h-4 mt-0.5 shrink-0 text-muted-foreground" />
              <span className="flex flex-col gap-0.5 flex-1 min-w-0">
                <span className="flex items-center gap-2">
                  {m.label}
                  {m.value === currentMode && <Check className="w-3 h-3 shrink-0 text-primary" />}
                </span>
                <span className="text-[10px] text-muted-foreground leading-tight">{m.description}</span>
              </span>
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
