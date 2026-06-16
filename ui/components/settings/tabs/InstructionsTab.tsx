'use client'
import React, { useEffect, useState } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Loader2, ExternalLink } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { ScopeSelector } from '@/components/settings/ScopeSelector'

interface InstructionsData {
  path: string
  filename: string
  content: string
  scope: string
}

interface Props {
  projectDir?: string | null
}

// scope is 'global' or a project_dir path (the ScopeSelector contract).
function scopeParams(scope: string) {
  const isGlobal = scope === 'global'
  return { scope: isGlobal ? 'global' : 'project', project_dir: isGlobal ? undefined : scope }
}

export function InstructionsTab({ projectDir }: Props) {
  const [scope, setScope] = useState<string>(projectDir || 'global')
  const [content, setContent] = useState('')
  const [meta, setMeta] = useState<InstructionsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setLoading(true)
    const { scope: s, project_dir } = scopeParams(scope)
    const qs = new URLSearchParams({ scope: s })
    if (project_dir) qs.set('project_dir', project_dir)
    apiFetch<InstructionsData>(`/api/project-instructions?${qs.toString()}`)
      .then(data => {
        setMeta(data)
        setContent(data.content)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [scope])

  const handleSave = async () => {
    setSaving(true)
    const { scope: s, project_dir } = scopeParams(scope)
    const data = await apiFetch<InstructionsData>('/api/project-instructions', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: s, project_dir, content }),
    })
    setMeta(prev => (prev ? { ...prev, ...data } : data))
    setSaving(false)
  }

  const handleEditFile = () => {
    const { scope: s, project_dir } = scopeParams(scope)
    apiFetch('/api/project-instructions/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: s, project_dir }),
    }).catch(() => {})
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Instructions</h3>
          <p className="text-xs text-muted-foreground">
            Directives injected into the system prompt (AGENTS.md / CLAUDE.md).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleEditFile}
            className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
            title="Open instructions file in editor"
          >
            <ExternalLink className="w-3 h-3" />
            Edit file
          </button>
          <Label className="text-xs text-muted-foreground">Scope:</Label>
          <ScopeSelector value={scope} onChange={setScope} />
        </div>
      </div>
      <Separator />

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
            {saving ? 'Saving...' : `Save ${scope === 'global' ? 'global' : 'project'} instructions`}
          </Button>
        </div>
      )}
    </div>
  )
}
