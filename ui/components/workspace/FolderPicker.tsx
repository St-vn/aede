'use client'
import React from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { FolderOpen } from 'lucide-react'
import { apiFetch } from '@/lib/api'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (path: string) => void
}

export function FolderPicker({ open, onOpenChange, onSelect }: Props) {
  const handlePick = async () => {
    try {
      const { path } = await apiFetch<{ path: string | null }>('/api/workspace/pick-directory', {
        method: 'POST',
      })
      if (path) {
        onSelect(path)
        onOpenChange(false)
      }
    } catch (e: any) {
      console.error('Folder picker failed:', e)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Select Project Directory</DialogTitle>
          <DialogDescription>
            Opens your system file explorer. Pick the root folder of your project.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center gap-4 py-4">
          <Button size="lg" onClick={handlePick} className="gap-2 w-full">
            <FolderOpen className="w-5 h-5" />
            Open File Explorer
          </Button>
          <p className="text-xs text-muted-foreground text-center">
            A native folder picker will open on the server. Select your project directory.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
