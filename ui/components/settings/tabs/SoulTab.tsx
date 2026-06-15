'use client'
import React, { useEffect, useState } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'

interface SoulData {
  name: string | null
  phonetic: string | null
  wake_word: string | null
  aliases: string[]
  persona: string
}

export function SoulTab() {
  const [soul, setSoul] = useState<SoulData | null>(null)
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [phonetic, setPhonetic] = useState('')
  const [wakeWord, setWakeWord] = useState('')
  const [voiceInputEnabled, setVoiceInputEnabled] = useState(false)
  const [voiceWakeWordEnabled, setVoiceWakeWordEnabled] = useState(false)

  useEffect(() => {
    Promise.all([
      fetch('/api/soul').then(r => r.json()),
      fetch('/api/config').then(r => r.json()),
    ]).then(([soulData, configData]) => {
      setSoul(soulData)
      setName(soulData.name || '')
      setPhonetic(soulData.phonetic || '')
      setWakeWord(soulData.wake_word || '')
      setVoiceInputEnabled(configData.voice_input_enabled ?? false)
      setVoiceWakeWordEnabled(configData.voice_wake_word_enabled ?? false)
      setLoading(false)
    })
  }, [])

  const handleSave = async () => {
    const body: Record<string, string | null> = {}
    if (name) body.name = name
    if (phonetic) body.phonetic = phonetic
    if (wakeWord) body.wake_word = wakeWord
    await fetch('/api/soul', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const resp = await fetch('/api/soul')
    const updated = await resp.json()
    setSoul(updated)
    setName(updated.name || '')
    setPhonetic(updated.phonetic || '')
    setWakeWord(updated.wake_word || '')
  }

  const toggleVoiceInput = async (val: boolean) => {
    setVoiceInputEnabled(val)
    await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'voice_input_enabled', value: val, scope: 'global' }),
    })
  }

  const toggleVoiceWakeWord = async (val: boolean) => {
    setVoiceWakeWordEnabled(val)
    await fetch('/api/config', {
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
        <p className="text-xs text-muted-foreground">Configure the agent&apos;s name, wake word, and persona.</p>
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
        <Button size="sm" className="h-8 text-xs" onClick={handleSave}>
          Save
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
      {soul && soul.persona && (
        <>
          <Separator />
          <div>
            <h4 className="text-xs font-medium mb-1">Persona</h4>
            <pre className="text-xs text-muted-foreground whitespace-pre-wrap bg-muted/30 rounded-md p-3">{soul.persona}</pre>
          </div>
        </>
      )}
    </div>
  )
}
