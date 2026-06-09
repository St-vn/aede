'use client'
import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormModal } from '@/components/ui/form-modal'
import { apiFetch } from '@/lib/api'
import type { AgentInfo } from '@/hooks/useAgents'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: 'add' | 'edit'
  agent?: AgentInfo
  scope?: string
  projectDir?: string
  onSave: (data: Record<string, unknown>) => void
  onDelete?: () => void
}

export function AgentFormDialog({ open, onOpenChange, mode, agent, scope, projectDir, onSave, onDelete }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [model, setModel] = useState('inherit')
  const [skills, setSkills] = useState('')
  const [tools, setTools] = useState('')
  const [disallowedTools, setDisallowedTools] = useState('')
  const [maxTurns, setMaxTurns] = useState('20')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [body, setBody] = useState('')

  useEffect(() => {
    if (open) {
      if (mode === 'edit' && agent) {
        setName(agent.name)
        setDescription(agent.description)
        setModel(agent.model || 'inherit')
        setSkills((agent.skills || []).join(', '))
        setTools((agent.tools || []).join(', '))
        setDisallowedTools((agent.disallowed_tools || []).join(', '))
        setMaxTurns(String(agent.max_turns ?? 20))
        setSystemPrompt(agent.system_prompt || '')
        setBody(agent.body || '')
      } else {
        setName('')
        setDescription('')
        setModel('inherit')
        setSkills('')
        setTools('')
        setDisallowedTools('')
        setMaxTurns('20')
        setSystemPrompt('')
        setBody('')
      }
    }
  }, [open, mode, agent])

  const handleSave = () => {
    if (!name.trim() || !description.trim()) return
    const data: Record<string, unknown> = {
      name: name.trim(),
      description: description.trim(),
      model: model.trim() || 'inherit',
      skills: skills.trim() ? skills.split(',').map(s => s.trim()).filter(Boolean) : [],
      tools: tools.trim() ? tools.split(',').map(s => s.trim()).filter(Boolean) : [],
      disallowed_tools: disallowedTools.trim() ? disallowedTools.split(',').map(s => s.trim()).filter(Boolean) : [],
      max_turns: parseInt(maxTurns) || 20,
      system_prompt: systemPrompt,
      body,
    }
    onSave(data)
    onOpenChange(false)
  }

  return (
    <FormModal open={open} onOpenChange={onOpenChange} title={mode === 'add' ? 'Add Agent' : 'Edit Agent'}
      filePath={mode === 'edit' ? agent?.file_path : undefined}
      onOpenFile={mode === 'edit' && agent ? () => apiFetch(`/api/agents/${encodeURIComponent(agent.name)}/open?scope=${scope || 'global'}${projectDir ? `&project_dir=${encodeURIComponent(projectDir)}` : ''}`, { method: 'POST' }) : undefined}>
      <div className="space-y-3">
          <Field label="Name">
            <Input value={name} onChange={e => setName(e.target.value)} className="h-8 text-xs" placeholder="my-agent" disabled={mode === 'edit'} />
          </Field>
          <Field label="Description">
            <Input value={description} onChange={e => setDescription(e.target.value)} className="h-8 text-xs" placeholder="What this agent does" />
          </Field>
          <Field label="Model">
            <Input value={model} onChange={e => setModel(e.target.value)} className="h-8 text-xs" placeholder="inherit" />
          </Field>
          <Field label="Skills (comma-separated)">
            <Input value={skills} onChange={e => setSkills(e.target.value)} className="h-8 text-xs" placeholder="research, search" />
          </Field>
          <Field label="Allowed tools (comma-separated, blank = all)">
            <Input value={tools} onChange={e => setTools(e.target.value)} className="h-8 text-xs" placeholder="web_search, read_file" />
          </Field>
          <Field label="Disallowed tools (comma-separated)">
            <Input value={disallowedTools} onChange={e => setDisallowedTools(e.target.value)} className="h-8 text-xs" placeholder="powershell, write_file" />
          </Field>
          <Field label="Max turns">
            <Input value={maxTurns} onChange={e => setMaxTurns(e.target.value)} className="h-8 text-xs" placeholder="20" type="number" min={1} />
          </Field>
          <Field label="System prompt">
            <Textarea value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} className="text-xs min-h-[60px]" placeholder="Custom system prompt for this agent" />
          </Field>
          <Field label="Body">
            <Textarea value={body} onChange={e => setBody(e.target.value)} className="text-xs min-h-[80px]" placeholder="Additional body text after frontmatter" />
          </Field>
          <div className="flex items-center justify-between pt-2">
            <div>
              {mode === 'edit' && onDelete && (
                <Button variant="destructive" size="sm" className="h-8 text-xs" onClick={() => { onDelete(); onOpenChange(false) }}>
                  Delete
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="h-8 text-xs" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button size="sm" className="h-8 text-xs" onClick={handleSave} disabled={!name.trim() || !description.trim()}>
                {mode === 'add' ? 'Create' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
    </FormModal>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  )
}
