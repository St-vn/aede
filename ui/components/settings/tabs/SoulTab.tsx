'use client'
import React, { useEffect, useState } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Loader2, ExternalLink } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { ScopeSelector } from '@/components/settings/ScopeSelector'

interface SoulData {
  name: string | null
  phonetic: string | null
  wake_word: string | null
  aliases: string[]
  persona: string
}

interface Props {
  projectDir?: string | null
}

// scope is 'global' or a project_dir path (the ScopeSelector contract).
function scopeParams(scope: string) {
  const isGlobal = scope === 'global'
  return { scope: isGlobal ? 'global' : 'project', project_dir: isGlobal ? undefined : scope }
}

export function SoulTab({ projectDir }: Props) {
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [phonetic, setPhonetic] = useState('')
  const [wakeWord, setWakeWord] = useState('')
  const [persona, setPersona] = useState('')
  const [scope, setScope] = useState<string>(projectDir || 'global')
  const [voiceInputEnabled, setVoiceInputEnabled] = useState(false)
  const [voiceWakeWordEnabled, setVoiceWakeWordEnabled] = useState(false)

  // Reload identity for the selected scope so the editor shows that file's content.
  useEffect(() => {
    setLoading(true)
    const { scope: s, project_dir } = scopeParams(scope)
    const qs = new URLSearchParams({ scope: s })
    if (project_dir) qs.set('project_dir', project_dir)
    Promise.all([
      apiFetch<SoulData>(`/api/soul?${qs.toString()}`),
      apiFetch<{ voice_input_enabled?: boolean; voice_wake_word_enabled?: boolean }>('/api/config'),
    ]).then(([soulData, configData]) => {
      setName(soulData.name || '')
      setPhonetic(soulData.phonetic || '')
      setWakeWord(soulData.wake_word || '')
      setPersona(soulData.persona || '')
      setVoiceInputEnabled(configData.voice_input_enabled ?? false)
      setVoiceWakeWordEnabled(configData.voice_wake_word_enabled ?? false)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [scope])

  const handleSave = async () => {
    const { scope: s, project_dir } = scopeParams(scope)
    const body: Record<string, string | null | undefined> = {
      scope: s,
      project_dir,
      name: name || null,
      phonetic: phonetic || null,
      wake_word: wakeWord || null,
      persona,
    }
    const updated = await apiFetch<SoulData>('/api/soul', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    setName(updated.name || '')
    setPhonetic(updated.phonetic || '')
    setWakeWord(updated.wake_word || '')
    setPersona(updated.persona || '')
  }

  const handleEditFile = () => {
    const { scope: s, project_dir } = scopeParams(scope)
    apiFetch('/api/soul/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: s, project_dir }),
    }).catch(() => {})
  }

  const toggleVoiceInput = async (val: boolean) => {
    setVoiceInputEnabled(val)
    await apiFetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'voice_input_enabled', value: val, scope: 'global' }),
    })
  }

  const toggleVoiceWakeWord = async (val: boolean) => {
    setVoiceWakeWordEnabled(val)
    await apiFetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'voice_wake_word_enabled', value: val, scope: 'global' }),
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Agent Identity</h3>
          <p className="text-xs text-muted-foreground">Name, wake word, and persona (SOUL.md).</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleEditFile}
            className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
            title="Open SOUL.md in editor"
          >
            <ExternalLink className="w-3 h-3" />
            Edit file
          </button>
          <Label className="text-xs text-muted-foreground">Scope:</Label>
          <ScopeSelector value={scope} onChange={setScope} />
        </div>
      </div>
      <Separator />
      <div className="space-y-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Name</label>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="e.g. Jarvis"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Phonetic</label>
          <input
            value={phonetic}
            onChange={e => setPhonetic(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="/ˈdʒɑːvɪs/"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Wake word</label>
          <input
            value={wakeWord}
            onChange={e => setWakeWord(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="e.g. hey jarvis"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium">Persona</label>
          <textarea
            value={persona}
            onChange={e => setPersona(e.target.value)}
            rows={6}
            className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono resize-y"
            placeholder="Freeform identity / tone / boundaries (Markdown). Injected into the system prompt."
          />
        </div>
        <Button size="sm" className="h-8 text-xs" onClick={handleSave}>
          Save {scope === 'global' ? 'global' : 'project'} identity
        </Button>
      </div>
      <Separator />
      <div>
        <h3 className="text-sm font-medium">Voice Input</h3>
        <p className="text-xs text-muted-foreground">
          Enable voice input via browser speech recognition. Audio is sent to your browser&apos;s STT service (Chrome routes to Google). Only recognized text is sent to the agent.
        </p>
      </div>
      <div className="space-y-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={voiceInputEnabled}
            onChange={e => toggleVoiceInput(e.target.checked)}
            className="rounded border-input"
          />
          <span className="text-xs font-medium">Push-to-talk mic button</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={voiceWakeWordEnabled}
            onChange={e => toggleVoiceWakeWord(e.target.checked)}
            className="rounded border-input"
          />
          <span className="text-xs font-medium">Continuous wake word listening</span>
        </label>
        <p className="text-xs text-muted-foreground">
          Voice input uses your browser&apos;s speech-to-text (Chrome routes audio to Google). Audio is not recorded by aede; only the resulting text is sent to the agent. Requires an internet connection.
        </p>
      </div>
    </div>
  )
}
