'use client'
import React from 'react'
import { Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

const MODELS = [
  { id: 'claude-sonnet-4', label: 'Sonnet 4' },
  { id: 'claude-opus-4',   label: 'Opus 4'   },
  { id: 'claude-haiku-4',  label: 'Haiku 4'  },
]

interface Props { currentModel: string; onModelChange: (m: string) => void }

export function ModelSelector({ currentModel, onModelChange }: Props) {
  const current = MODELS.find(m => m.id === currentModel) ?? { id: currentModel, label: currentModel }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={
        <Button variant="ghost" size="sm" aria-label="Select model" className="text-xs text-muted-foreground gap-1">
          {current.label}
        </Button>
      } />
      <DropdownMenuContent align="end">
        {MODELS.map(m => (
          <DropdownMenuItem key={m.id} onClick={() => onModelChange(m.id)}>
            {m.id === currentModel && <Check className="w-3 h-3 mr-2" />}
            {m.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
