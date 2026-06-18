'use client'
import React from 'react'
import { Check, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const MODES = [
  { value: 'plan', label: 'Plan', description: 'Read-only. Writes and shell denied.' },
  { value: 'normal', label: 'Normal', description: 'Read auto, writes/shell gated.' },
  { value: 'allow_write_read', label: 'Write+Read', description: 'Read + file writes auto, shell gated.' },
  { value: 'execution', label: 'Execution', description: 'Auto-approve with safety classifier.' },
  { value: 'auto', label: 'Auto', description: 'Hands-free. All tools run.' },
]

interface Props {
  currentMode: string
  onModeChange: (mode: string) => void
}

export function ModeSelector({ currentMode, onModeChange }: Props) {
  const current = MODES.find(m => m.value === currentMode) ?? MODES[1]

  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={
        <Button variant="ghost" size="sm" aria-label="Select permission mode"
          className="text-xs text-muted-foreground gap-1 max-w-[100px] truncate">
          <Shield className="w-3 h-3 shrink-0" />
          {current.label}
        </Button>
      } />
      <DropdownMenuContent align="end" className="min-w-[200px]">
        <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Permission Mode
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {MODES.map(m => (
          <DropdownMenuItem key={m.value} onClick={() => onModeChange(m.value)} className="text-xs flex flex-col items-start gap-0.5 py-1.5">
            <span className="flex items-center gap-2 w-full">
              {m.value === currentMode && <Check className="w-3 h-3 shrink-0" />}
              <span className={m.value !== currentMode ? 'ml-5' : ''}>{m.label}</span>
            </span>
            <span className="text-[10px] text-muted-foreground ml-5 leading-tight">{m.description}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
