'use client'
import React, { useEffect, useState } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'
import { apiFetch } from '@/lib/api'

interface InstructionsData {
  path: string
  filename: string
  content: string
  scope: string
}

type Scope = 'global' | 'project'

interface Props {
  projectDir?: string | null
}

export function InstructionsTab({ projectDir }: Props) {
  const [scope, setScope] = useState<Scope>('project')
  const [content, setContent] = useState('')
  const [meta, setMeta] = useState<InstructionsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const canProject = !!projectDir
  const effectiveScope: Scope = scope === 'project' && !canProject ? 'global' : scope

  useEffect(() => {
    setLoading(true)
    const qs = new URLSearchParams({ scope: effectiveScope })
    if (effectiveScope === 'project' && projectDir) qs.set('project_dir', projectDir)
    apiFetch<InstructionsData>(`/api/project-instructions?${qs.toString()}`)
      .then(data => {
        setMeta(data)
        setContent(data.content)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [effectiveScope, projectDir])

  const handleSave = async () => {
    setSaving(true)
    const data = await apiFetch<InstructionsData>('/api/project-instructions', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scope: effectiveScope,
        project_dir: effectiveScope === 'project' ? projectDir : undefined,
        content,
      }),
    })
    setMeta(prev => (prev ? { ...prev, ...data } : data))
    setSaving(false)
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium">Instructions</h3>
        <p className="text-xs text-muted-foreground">
          Freeform directives injected into the system prompt. Global lives in{' '}
          <code className="text-[10px]">~/.aede/AGENTS.md</code>; project is the active repo&apos;s{' '}
          <code className="text-[10px]">AGENTS.md</code> (or <code className="text-[10px]">CLAUDE.md</code>).
        </p>
      </div>
      <Separator />
      <div className="flex items-center gap-1 rounded-md bg-muted/40 p-0.5 w-fit">
        {(['global', 'project'] as Scope[]).map(s => {
          const disabled = s === 'project' && !canProject
          return (
            <button
              key={s}
              type="button"
              disabled={disabled}
              onClick={() => setScope(s)}
              className={`px-2.5 py-1 text-xs rounded capitalize transition-colors ${
                effectiveScope === s ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground'
              } ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
              title={disabled ? 'Open a project to edit project instructions' : undefined}
            >
              {s}
            </button>
          )
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-3">
          {meta && (
            <p className="text-[10px] font-mono text-muted-foreground truncate">{meta.path}</p>
          )}
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            rows={16}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono resize-y"
            placeholder={`# Instructions\n\nProject conventions, rules, and context for the agent...`}
          />
          <Button size="sm" className="h-8 text-xs" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : `Save ${effectiveScope} instructions`}
          </Button>
        </div>
      )}
    </div>
  )
}
