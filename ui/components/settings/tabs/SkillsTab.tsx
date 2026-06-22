'use client'
import React, { useState, useRef } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { useSkills, useCreateSkill, useUpdateSkill, useDeleteSkill, useUploadSkill, type SkillInfo } from '@/hooks/useSkills'
import { SkillFormDialog } from './SkillFormDialog'
import { Sparkles, Plus, Pencil, Trash2, Upload } from 'lucide-react'
import { ScopeSelector } from '@/components/settings/ScopeSelector'
import { apiFetch } from '@/lib/api'

export function SkillsTab() {
  const { data: skills = [], isLoading } = useSkills()
  const createSkill = useCreateSkill()
  const updateSkill = useUpdateSkill()
  const deleteSkill = useDeleteSkill()
  const uploadSkill = useUploadSkill()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<'add' | 'edit'>('add')
  const [editingSkill, setEditingSkill] = useState<SkillInfo | undefined>()
  const [scope, setScope] = useState('global')
  const [uploadError, setUploadError] = useState<string | null>(null)

  const projectDir = scope !== 'global' ? scope : undefined

  const handleAdd = () => {
    setEditingSkill(undefined)
    setDialogMode('add')
    setDialogOpen(true)
  }

  const handleEdit = (skill: SkillInfo) => {
    setEditingSkill(skill)
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
      await apiFetch(`/api/skills/upload?${params}`, { method: 'POST', body: (() => { const f = new FormData(); f.append('file', file); return f; })() })
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Skills</h3>
          <p className="text-xs text-muted-foreground">Instruction bundles injected into the system prompt.</p>
        </div>
        <div className="flex items-center gap-2">
          <ScopeSelector value={scope} onChange={setScope} />
          <input ref={fileInputRef} type="file" accept=".md,.skill" className="hidden" onChange={handleUpload} />
          <Button size="sm" className="h-8 text-xs gap-1" variant="outline" onClick={() => fileInputRef.current?.click()}>
            <Upload className="w-3.5 h-3.5" /> Import .md
          </Button>
          <Button size="sm" className="h-8 text-xs gap-1" onClick={handleAdd}>
            <Plus className="w-3.5 h-3.5" /> Add Skill
          </Button>
        </div>
      </div>
      <Separator />
      {uploadError && (
        <p className="text-xs text-destructive bg-destructive/10 px-3 py-1.5 rounded-md">{uploadError}</p>
      )}
      {skills.length === 0 && !isLoading && (
        <p className="text-xs text-muted-foreground">No skills found. Create or import one to augment agent capabilities.</p>
      )}
      <div className="space-y-2">
        {skills.map(skill => (
          <div key={skill.name} className="px-3 py-2 rounded-md border border-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <Sparkles className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="text-sm font-medium truncate">{skill.name}</span>
              </div>
              <div className="flex items-center gap-1 shrink-0 ml-2">
                <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground" onClick={() => handleEdit(skill)} aria-label={`Edit ${skill.name}`}>
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive" onClick={() => deleteSkill.mutate({ name: skill.name, scope, project_dir: projectDir })} aria-label={`Delete ${skill.name}`}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            {skill.description && (
              <p className="text-xs text-muted-foreground mt-1">{skill.description}</p>
            )}
            {skill.trigger_phrases && skill.trigger_phrases.length > 0 && (
              <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                {skill.trigger_phrases.map(p => (
                  <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{p}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <SkillFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        skill={editingSkill}
        scope={scope}
        projectDir={projectDir}
        onSave={dialogMode === 'add' ? (data) => createSkill.mutate({ ...data, scope, project_dir: projectDir }) : (data) => updateSkill.mutate({ name: editingSkill!.name, ...data, scope, project_dir: projectDir })}
        onDelete={editingSkill ? () => deleteSkill.mutate({ name: editingSkill.name, scope, project_dir: projectDir }) : undefined}
      />
    </div>
  )
}
