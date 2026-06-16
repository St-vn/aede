'use client'
import React, { useEffect, useState } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'
import { apiFetch } from '@/lib/api'

interface SoulData {
  name: string | null
  phonetic: string | null
  wake_word: string | null
  aliases: string[]
  persona: string
}

type Scope = 'global' | 'project'

interface Props {
  projectDir?: string | null
}

export function SoulTab({ projectDir }: Props) {
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [phonetic, setPhonetic] = useState('')
  const [wakeWord, setWakeWord] = useState('')
  const [persona, setPersona] = useState('')
  const [scope, setScope] = useState<Scope>('global')
  const [voiceInputEnabled, setVoiceInputEnabled] = useState(false)
  const [voiceWakeWordEnabled, setVoiceWakeWordEnabled] = useState(false)

  // Project scope is only meaningful when a project is active.
  const canProject = !!projectDir
  const effectiveScope: Scope = scope === 'project' && !canProject ? 'global' : scope

  useEffect(() => {
    Promise.all([
      apiFetch<SoulData>('/api/soul'),
      apiFetch<{ voice_input_enabled?: boolean; voice_wake_word_enabled?: boolean }>('/api/config'),
    ]).then(([soulData, configData]) => {
      setName(soulData.name || '')
      setPhonetic(soulData.phonetic || '')
      setWakeWord(soulData.wake_word || '')
      setPersona(soulData.persona || '')
      setVoiceInputEnabled(configData.voice_input_enabled ?? false)
      setVoiceWakeWordEnabled(configData.voice_wake_word_enabled ?? false)
      setLoading(false)
    })
  }, [])

  const handleSave = async () => {
    const body: Record<string, string | null> = {
      scope: effectiveScope,
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
      <div>
        <h3 className="text-sm font-medium">Agent Identity</h3>
        <p className="text-xs text-muted-foreground">Configure the agent&apos;s name, wake word, and persona (SOUL.md).</p>
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
              title={disabled ? 'Open a project to edit project-scoped identity' : undefined}
            >
              {s}
            </button>
          )
        })}
      </div>
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
          Save {effectiveScope === 'project' ? 'project' : 'global'} identity
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
