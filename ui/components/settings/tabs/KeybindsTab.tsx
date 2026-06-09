'use client'
import React from 'react'
import { Separator } from '@/components/ui/separator'

const SHORTCUTS = [
  { keys: ['Ctrl', 'K'], description: 'Open command palette' },
  { keys: ['Ctrl', 'Enter'], description: 'Send message' },
  { keys: ['Shift', 'Enter'], description: 'New line in input' },
  { keys: ['/'], description: 'Open slash commands' },
  { keys: ['@'], description: 'Mention files' },
  { keys: ['Ctrl', 'L'], description: 'Clear conversation' },
  { keys: ['Ctrl', 'N'], description: 'New session' },
  { keys: ['Ctrl', ','], description: 'Open settings' },
]

export function KeybindsTab() {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Keyboard Shortcuts</h3>
      <Separator />
      <div className="space-y-1">
        {SHORTCUTS.map((shortcut, i) => (
          <div key={i} className="flex items-center justify-between px-3 py-2 rounded-md hover:bg-muted/50">
            <span className="text-xs">{shortcut.description}</span>
            <div className="flex items-center gap-1">
              {shortcut.keys.map((key, j) => (
                <React.Fragment key={j}>
                  {j > 0 && <span className="text-xs text-muted-foreground">+</span>}
                  <kbd className="px-1.5 py-0.5 text-[10px] font-mono rounded border border-border bg-muted shadow-sm">{key}</kbd>
                </React.Fragment>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
