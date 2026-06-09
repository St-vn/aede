'use client'
import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormModal } from '@/components/ui/form-modal'
import { apiFetch } from '@/lib/api'
import type { SkillInfo } from '@/hooks/useSkills'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: 'add' | 'edit'
  skill?: SkillInfo
  scope?: string
  projectDir?: string
  onSave: (data: Record<string, unknown>) => void
  onDelete?: () => void
}

export function SkillFormDialog({ open, onOpenChange, mode, skill, scope, projectDir, onSave, onDelete }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [triggerPhrases, setTriggerPhrases] = useState('')
  const [allowedTools, setAllowedTools] = useState('')
  const [model, setModel] = useState('')
  const [body, setBody] = useState('')

  useEffect(() => {
    if (open) {
      if (mode === 'edit' && skill) {
        setName(skill.name)
        setDescription(skill.description)
        setTriggerPhrases((skill.trigger_phrases || []).join(', '))
        setAllowedTools((skill.allowed_tools || []).join(', '))
        setModel(skill.model || '')
        setBody(skill.body || '')
      } else {
        setName('')
        setDescription('')
        setTriggerPhrases('')
        setAllowedTools('')
        setModel('')
        setBody('')
      }
    }
  }, [open, mode, skill])

  const handleSave = () => {
    if (!name.trim() || !description.trim()) return
    const data: Record<string, unknown> = {
      name: name.trim(),
      description: description.trim(),
      trigger_phrases: triggerPhrases.trim() ? triggerPhrases.split(',').map(s => s.trim()).filter(Boolean) : [],
      allowed_tools: allowedTools.trim() ? allowedTools.split(',').map(s => s.trim()).filter(Boolean) : [],
      model: model.trim() || null,
      body,
    }
    onSave(data)
    onOpenChange(false)
  }

  return (
    <FormModal open={open} onOpenChange={onOpenChange} title={mode === 'add' ? 'Add Skill' : 'Edit Skill'}
      filePath={mode === 'edit' ? skill?.file_path : undefined}
      onOpenFile={mode === 'edit' && skill ? () => apiFetch(`/api/skills/${encodeURIComponent(skill.name)}/open?scope=${scope || 'global'}${projectDir ? `&project_dir=${encodeURIComponent(projectDir)}` : ''}`, { method: 'POST' }) : undefined}>
      <div className="space-y-3">
          <Field label="Name">
            <Input value={name} onChange={e => setName(e.target.value)} className="h-8 text-xs" placeholder="my-skill" disabled={mode === 'edit'} />
          </Field>
          <Field label="Description">
            <Input value={description} onChange={e => setDescription(e.target.value)} className="h-8 text-xs" placeholder="What this skill does" />
          </Field>
          <Field label="Trigger phrases (comma-separated)">
            <Input value={triggerPhrases} onChange={e => setTriggerPhrases(e.target.value)} className="h-8 text-xs" placeholder="research, find info, look up" />
          </Field>
          <Field label="Allowed tools (comma-separated, blank = all)">
            <Input value={allowedTools} onChange={e => setAllowedTools(e.target.value)} className="h-8 text-xs" placeholder="web_search, read_file" />
          </Field>
          <Field label="Model (blank = inherit)">
            <Input value={model} onChange={e => setModel(e.target.value)} className="h-8 text-xs" placeholder="claude-sonnet-4-20250514" />
          </Field>
          <Field label="Body">
            <Textarea value={body} onChange={e => setBody(e.target.value)} className="text-xs min-h-[80px]" placeholder="Skill instruction content" />
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
