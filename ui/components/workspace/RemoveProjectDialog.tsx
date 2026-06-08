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
  'delete-folder': 'Delete project folder',
  'remove-git': 'Remove git repository',
}

const BUTTONS: Record<Action, { label: string; variant: 'default' | 'destructive' }> = {
  'remove': { label: 'Remove', variant: 'default' },
  'delete-folder': { label: 'Delete Folder', variant: 'destructive' },
  'remove-git': { label: 'Remove .git', variant: 'destructive' },
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
          <DialogTitle>Remove "{projectName}"</DialogTitle>
          <DialogDescription>
            Choose what to do with this project.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <select
            value={action}
            onChange={(e) => setAction(e.target.value as Action)}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="remove">{LABELS['remove']}</option>
            <option value="delete-folder">{LABELS['delete-folder']}</option>
            <option value="remove-git">{LABELS['remove-git']}</option>
          </select>

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
