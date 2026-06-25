'use client'
import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { useLearnings, useAddLearning, useDeleteLearning } from '@/hooks/useMemory'
import { Plus, Trash2, BrainCircuit } from 'lucide-react'

export function MemoryTab() {
  const { data: learnings = [], isLoading } = useLearnings()
  const addLearning = useAddLearning()
  const deleteLearning = useDeleteLearning()
  const [newContent, setNewContent] = useState('')

  const handleAdd = async () => {
    if (!newContent.trim()) return
    await addLearning.mutateAsync({ content: newContent.trim() })
    setNewContent('')
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Learnings (Memory)</h3>
      <Separator />
      <div className="space-y-2">
        {learnings.length === 0 && !isLoading && (
          <p className="text-xs text-muted-foreground">No learnings stored yet.</p>
        )}
        {learnings.map(l => (
          <div key={l.id} className="flex items-start gap-2 px-3 py-2 rounded-md border border-border/60">
            <BrainCircuit className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs">{l.content}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] px-1 py-0.5 rounded bg-muted text-muted-foreground">{l.type}</span>
                <span className="text-xs text-muted-foreground/50">
                  {new Date(l.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <Button variant="ghost" size="icon-sm" className="h-6 w-6 shrink-0 text-muted-foreground hover:text-destructive"
              onClick={() => deleteLearning.mutate(l.id)}>
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        ))}
      </div>
      <Separator />
      <div className="flex items-center gap-2">
        <Input placeholder="New learning..." className="flex-1 h-8 text-xs"
          value={newContent} onChange={e => setNewContent(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleAdd() }} />
        <Button size="sm" className="h-8 text-xs" onClick={handleAdd} disabled={!newContent.trim()}>
          <Plus className="w-3 h-3 mr-1" /> Add
        </Button>
      </div>
    </div>
  )
}
