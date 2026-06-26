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

// ASR transcription models (mirrors aede/asr.py ASR_MODELS). Ordered cheapest
// first; prices verified against provider docs 2026-06-17. label → model id.
const ASR_CHOICES: { id: string; label: string }[] = [
  { id: 'whisper-large-v3-turbo', label: 'Whisper Turbo · Groq · ~$0.04/hr (free tier, cheapest)' },
  { id: 'parakeet-tdt-0.6b-v3', label: 'Parakeet TDT 0.6B · OpenRouter · $0.0015/min' },
  { id: 'qwen3-asr-flash', label: 'Qwen3 ASR Flash · OpenRouter · ~$0.0021/min' },
  { id: 'voxtral-mini-transcribe', label: 'Voxtral Mini · OpenRouter · $0.003/min' },
  { id: 'whisper-large-v3', label: 'Whisper Large V3 · Groq/OpenRouter · most accurate' },
  { id: 'chirp-3', label: 'Chirp 3 · Google/OpenRouter' },
]

// Prebuilt wake-word models bundled with openwakeword-wasm-browser.
const WAKE_CHOICES: { id: string; label: string }[] = [
  { id: 'hey_jarvis', label: '"Hey Jarvis"' },
  { id: 'alexa', label: '"Alexa"' },
  { id: 'hey_mycroft', label: '"Hey Mycroft"' },
  { id: 'hey_rhasspy', label: '"Hey Rhasspy"' },
]

// Per-provider API key env names for BYOK (keys stored in aede's vault).
const PROVIDER_KEYS: { env: string; provider: string; label: string }[] = [
  { env: 'GROQ_API_KEY', provider: 'groq', label: 'Groq (free tier — default)' },
  { env: 'OPENAI_API_KEY', provider: 'openai', label: 'OpenAI' },
  { env: 'GOOGLE_API_KEY', provider: 'google', label: 'Google AI (Chirp 3)' },
  { env: 'OPENROUTER_API_KEY', provider: 'openrouter', label: 'OpenRouter (Parakeet/Qwen3/Voxtral)' },
]

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
  const [asrModel, setAsrModel] = useState('whisper-large-v3-turbo')
  const [wakeModel, setWakeModel] = useState('hey_jarvis')
  const [credNames, setCredNames] = useState<string[]>([])
  const [keyDrafts, setKeyDrafts] = useState<Record<string, string>>({})

  // Reload identity for the selected scope so the editor shows that file's content.
  useEffect(() => {
    setLoading(true)
    const { scope: s, project_dir } = scopeParams(scope)
    const qs = new URLSearchParams({ scope: s })
    if (project_dir) qs.set('project_dir', project_dir)
    Promise.all([
      apiFetch<SoulData>(`/api/soul?${qs.toString()}`),
      apiFetch<{ voice_input_enabled?: boolean; voice_wake_word_enabled?: boolean; voice_asr_model?: string; voice_wake_model?: string }>('/api/config'),
      apiFetch<{ name: string }[]>('/api/credentials').catch(() => []),
    ]).then(([soulData, configData, creds]) => {
      setName(soulData.name || '')
      setPhonetic(soulData.phonetic || '')
      setWakeWord(soulData.wake_word || '')
      setPersona(soulData.persona || '')
      setVoiceInputEnabled(configData.voice_input_enabled ?? false)
      setVoiceWakeWordEnabled(configData.voice_wake_word_enabled ?? false)
      setAsrModel(configData.voice_asr_model ?? 'whisper-large-v3-turbo')
      setWakeModel(configData.voice_wake_model ?? 'hey_jarvis')
      setCredNames(creds.map(c => c.name))
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

  const saveConfigKey = async (key: string, value: string) => {
    await apiFetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, value, scope: 'global' }),
    })
  }

  const saveKey = async (envName: string, provider: string) => {
    const value = keyDrafts[envName]?.trim()
    if (!value) return
    await apiFetch('/api/credentials', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: envName, value, provider }),
    })
    setCredNames(prev => prev.includes(envName) ? prev : [...prev, envName])
    setKeyDrafts(prev => ({ ...prev, [envName]: '' }))
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
      <div className="flex items-center justify-center py-12" aria-live="polite" aria-busy="true">
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
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
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
          <label htmlFor="soul-name" className="text-xs font-medium">Name</label>
          <input id="soul-name"
            value={name}
            onChange={e => setName(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="e.g. Jarvis"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="soul-phonetic" className="text-xs font-medium">Phonetic</label>
          <input id="soul-phonetic"
            value={phonetic}
            onChange={e => setPhonetic(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="/ˈdʒɑːvɪs/"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="soul-wake-word" className="text-xs font-medium">Wake word</label>
          <input id="soul-wake-word"
            value={wakeWord}
            onChange={e => setWakeWord(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="e.g. hey jarvis"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="soul-persona" className="text-xs font-medium">Persona</label>
          <textarea id="soul-persona"
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
          Wake word runs on-device (openWakeWord). Spoken commands are transcribed by your chosen ASR model below. With no API key, voice falls back to the browser&apos;s built-in speech recognition.
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

        <div className="space-y-1.5">
          <label htmlFor="soul-wake-model" className="text-xs font-medium">Wake word model</label>
          <select id="soul-wake-model"
            value={wakeModel}
            onChange={e => { setWakeModel(e.target.value); void saveConfigKey('voice_wake_model', e.target.value) }}
            className="flex h-8 w-full rounded-md border border-input bg-background px-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {WAKE_CHOICES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
          <p className="text-xs text-muted-foreground">
            On-device, no network. Only these prebuilt phrases are supported; a custom phrase requires training a model. (The &quot;Wake word&quot; text field above is for the agent&apos;s spoken-name display.)
          </p>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="soul-asr-model" className="text-xs font-medium">Transcription model (ASR)</label>
          <select id="soul-asr-model"
            value={asrModel}
            onChange={e => { setAsrModel(e.target.value); void saveConfigKey('voice_asr_model', e.target.value) }}
            className="flex h-8 w-full rounded-md border border-input bg-background px-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {ASR_CHOICES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium">API keys (bring your own)</label>
          <p className="text-xs text-muted-foreground">
            Stored in aede&apos;s credential vault. Set a key for the provider of your chosen model. No key = free browser speech fallback.
          </p>
          {PROVIDER_KEYS.map(pk => {
            const isSet = credNames.includes(pk.env)
            return (
              <div key={pk.env} className="flex items-center gap-2">
                <span className="text-[10px] w-44 shrink-0 text-muted-foreground">
                  {pk.label}{isSet ? ' ✓' : ''}
                </span>
                <input
                  type="password"
                  value={keyDrafts[pk.env] ?? ''}
                  onChange={e => setKeyDrafts(prev => ({ ...prev, [pk.env]: e.target.value }))}
                  placeholder={isSet ? 'saved — enter to replace' : pk.env}
                  className="flex h-7 flex-1 rounded-md border border-input bg-background px-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
                <Button size="sm" variant="outline" className="h-7 text-[10px]"
                  disabled={!keyDrafts[pk.env]?.trim()}
                  onClick={() => saveKey(pk.env, pk.provider)}>
                  Save
                </Button>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
