'use client'
import React, { useState, useRef } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { useAgents, useCreateAgent, useUpdateAgent, useDeleteAgent, useUploadAgent, type AgentInfo } from '@/hooks/useAgents'
import { AgentFormDialog } from './AgentFormDialog'
import { Bot, Wrench, Plus, Pencil, Trash2, Upload } from 'lucide-react'
import { ScopeSelector } from '@/components/settings/ScopeSelector'
import { apiFetch } from '@/lib/api'

export function AgentsTab() {
  const { data: agents = [], isLoading } = useAgents()
  const createAgent = useCreateAgent()
  const updateAgent = useUpdateAgent()
  const deleteAgent = useDeleteAgent()
  const uploadAgent = useUploadAgent()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<'add' | 'edit'>('add')
  const [editingAgent, setEditingAgent] = useState<AgentInfo | undefined>()
  const [scope, setScope] = useState('global')
  const [uploadError, setUploadError] = useState<string | null>(null)

  const projectDir = scope !== 'global' ? scope : undefined

  const handleAdd = () => {
    setEditingAgent(undefined)
    setDialogMode('add')
    setDialogOpen(true)
  }

  const handleEdit = (agent: AgentInfo) => {
    setEditingAgent(agent)
    setDialogMode('edit')
    setDialogOpen(true)
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadError(null)
    try {
      const params = new URLSearchParams({ scope })
      if (projectDir) params.set('project_dir', projectDir)
      await apiFetch(`/api/agents/upload?${params}`, { method: 'POST', body: (() => { const f = new FormData(); f.append('file', file); return f; })() })
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Agents</h3>
          <p className="text-xs text-muted-foreground">Subagent definitions for delegated tasks.</p>
        </div>
        <div className="flex items-center gap-2">
          <ScopeSelector value={scope} onChange={setScope} />
          <input ref={fileInputRef} type="file" accept=".md,.agent" className="hidden" onChange={handleUpload} />
          <Button size="sm" className="h-8 text-xs gap-1" variant="outline" onClick={() => fileInputRef.current?.click()}>
            <Upload className="w-3.5 h-3.5" /> Import .md
          </Button>
          <Button size="sm" className="h-8 text-xs gap-1" onClick={handleAdd}>
            <Plus className="w-3.5 h-3.5" /> Add Agent
          </Button>
        </div>
      </div>
      <Separator />
      {uploadError && (
        <p className="text-xs text-destructive bg-destructive/10 px-3 py-1.5 rounded-md">{uploadError}</p>
      )}
      {agents.length === 0 && !isLoading && (
        <p className="text-xs text-muted-foreground">No agents found. Create or import one to use subagent delegation.</p>
      )}
      <div className="space-y-2">
        {agents.map(agent => (
          <div key={agent.name} className="px-3 py-2 rounded-md border border-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <Bot className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-sm font-medium truncate">{agent.name}</span>
                {agent.model && agent.model !== 'inherit' && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">{agent.model}</span>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0 ml-2">
                <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground" onClick={() => handleEdit(agent)} title="Edit">
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive" onClick={() => deleteAgent.mutate({ name: agent.name, scope, project_dir: projectDir })} title="Delete">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            {agent.description && (
              <p className="text-xs text-muted-foreground mt-1">{agent.description}</p>
            )}
            <div className="flex items-center gap-1 mt-1.5 flex-wrap">
              {agent.tools && agent.tools.length > 0 && (
                <>
                  <Wrench className="w-3 h-3 text-muted-foreground" />
                  {agent.tools.map(t => (
                    <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{t}</span>
                  ))}
                </>
              )}
              {agent.skills && agent.skills.length > 0 && agent.skills.map(s => (
                <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">{s}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
      <AgentFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        agent={editingAgent}
        scope={scope}
        projectDir={projectDir}
        onSave={dialogMode === 'add' ? (data) => createAgent.mutate({ ...data, scope, project_dir: projectDir }) : (data) => updateAgent.mutate({ name: editingAgent!.name, ...data, scope, project_dir: projectDir })}
        onDelete={editingAgent ? () => deleteAgent.mutate({ name: editingAgent.name, scope, project_dir: projectDir }) : undefined}
      />
    </div>
  )
}
