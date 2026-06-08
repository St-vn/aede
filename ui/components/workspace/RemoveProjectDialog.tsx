'use client'
import React, { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'

import { Button } from '@/components/ui/button'
import { AlertTriangle } from 'lucide-react'

type Action = 'remove' | 'delete-folder' | 'remove-git'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectDir: string
  projectName: string
  onRemove: () => void
  onDeleteFolder: () => void
  onRemoveGit: () => void
}

const WARNINGS: Record<Action, string | null> = {
  'remove': null,
  'delete-folder': 'This will permanently delete the entire project folder from disk. This action cannot be undone.',
  'remove-git': 'This will permanently delete the .git directory. Git history will be lost. The project files will remain.',
}

const LABELS: Record<Action, string> = {
  'remove': 'Remove from list',
  'remove-git': 'Remove git repository',
  'delete-folder': 'Delete project folder',
}

const BUTTONS: Record<Action, { label: string; variant: 'default' | 'destructive' }> = {
  'remove': { label: 'Remove', variant: 'default' },
  'remove-git': { label: 'Remove .git', variant: 'destructive' },
  'delete-folder': { label: 'Delete Folder', variant: 'destructive' },
}

export function RemoveProjectDialog({ open, onOpenChange, projectDir, projectName, onRemove, onDeleteFolder, onRemoveGit }: Props) {
  const [action, setAction] = useState<Action>('remove')

  const handleConfirm = () => {
    if (action === 'remove') onRemove()
    else if (action === 'delete-folder') onDeleteFolder()
    else if (action === 'remove-git') onRemoveGit()
    onOpenChange(false)
  }

  const warning = WARNINGS[action]
  const button = BUTTONS[action]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Remove &ldquo;{projectName}&rdquo;</DialogTitle>
          <DialogDescription>
            Choose what to do with this project.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1">
          {(Object.keys(LABELS) as Action[]).map(a => (
            <button
              key={a}
              type="button"
              onClick={() => setAction(a)}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors text-left ${action === a
                  ? 'bg-accent text-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
            >
              {LABELS[a]}
            </button>
          ))}

          {warning && (
            <div className="flex gap-2 items-start text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <p>{warning}</p>
            </div>
          )}

          <p className="text-xs text-muted-foreground">{projectDir}</p>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button variant={button.variant} onClick={handleConfirm}>{button.label}</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
