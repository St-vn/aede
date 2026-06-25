'use client'
import React, { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { useConfigSources, useUpdateConfig } from '@/hooks/useConfig'
import { ScopeSelector } from '@/components/settings/ScopeSelector'
import { apiFetch } from '@/lib/api'
import { Save, ExternalLink } from 'lucide-react'
import { toast } from 'sonner'

interface ConfigField {
  key: string
  label: string
  type: 'text' | 'number' | 'boolean'
  description?: string
  category: string
}

const CONFIG_FIELDS: ConfigField[] = [
  { key: 'context_window', label: 'Context Window', type: 'number', category: 'Model', description: 'Max tokens in context window' },
  { key: 'compaction_threshold', label: 'Compaction Threshold', type: 'number', category: 'Model', description: '0.0-1.0, triggers compaction when exceeded' },
  { key: 'tool_output_max_tokens', label: 'Tool Output Max Tokens', type: 'number', category: 'Model' },
  { key: 'gate_mode', label: 'Gate Mode', type: 'text', category: 'Behavior' },
  { key: 'auto_approve', label: 'Auto-approve Tools', type: 'text', category: 'Behavior' },
  { key: 'shell', label: 'Shell', type: 'text', category: 'System', description: 'powershell, cmd, or wsl' },
  { key: 'grounding_enabled', label: 'Grounding', type: 'boolean', category: 'Features', description: 'Append grounding instruction to system prompt' },
  { key: 'critic_enabled', label: 'Critic', type: 'boolean', category: 'Features', description: 'Run critic pass before gated writes' },
  { key: 'ollama_base_url', label: 'Ollama Base URL', type: 'text', category: 'Ollama' },
  { key: 'ollama_embed_model', label: 'Ollama Embed Model', type: 'text', category: 'Ollama' },
  { key: 'learnings_top_k', label: 'Learnings Top K', type: 'number', category: 'Memory' },
  { key: 'learnings_max_tokens', label: 'Learnings Max Tokens', type: 'number', category: 'Memory' },
]

export function ConfigTab() {
  const [scope, setScope] = useState<string>('global')
  const [values, setValues] = useState<Record<string, string>>({})
  const { data: sources } = useConfigSources()
  const updateConfig = useUpdateConfig()

  const handleChange = (key: string, value: string) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async (key: string) => {
    const value = values[key]
    if (value === undefined) return
    try {
      await updateConfig.mutateAsync({ key, value, scope })
      const field = CONFIG_FIELDS.find(f => f.key === key)
      toast.success(`${field?.label ?? key} saved`)
    } catch (err) {
      const field = CONFIG_FIELDS.find(f => f.key === key)
      toast.error(`Failed to save ${field?.label ?? key}`)
    }
  }

  const handleToggle = async (key: string, checked: boolean) => {
    await updateConfig.mutateAsync({ key, value: String(checked), scope })
  }

  const categories = [...new Set(CONFIG_FIELDS.map(f => f.category))]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Configuration</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => apiFetch('/api/config/open', { method: 'POST', body: JSON.stringify({ scope }), headers: { 'Content-Type': 'application/json' } })}
            className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
            title="Open config file in editor"
          >
            <ExternalLink className="w-3 h-3" />
            Edit file
          </button>
          <Label className="text-xs text-muted-foreground">Scope:</Label>
          <ScopeSelector value={scope} onChange={setScope} />
        </div>
      </div>
      <Separator />
      {categories.map(cat => (
        <div key={cat} className="space-y-3">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{cat}</h4>
          {CONFIG_FIELDS.filter(f => f.category === cat).map(field => {
            const source = sources?.[field.key] || 'default'
            return (
              <div key={field.key} className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <Label className="text-xs" htmlFor={`cfg-${field.key}`}>{field.label}</Label>
                  {field.description && (
                    <p className="text-[10px] text-muted-foreground">{field.description}</p>
                  )}
                  <span className="text-[10px] text-muted-foreground">({source})</span>
                </div>
                {field.type === 'boolean' ? (
                  <Switch
                    id={`cfg-${field.key}`}
                    checked={values[field.key] === 'true'}
                    onCheckedChange={(c) => handleToggle(field.key, c)}
                  />
                ) : (
                  <div className="flex items-center gap-1">
                    <Input
                      id={`cfg-${field.key}`}
                      className="w-32 h-7 text-xs"
                      placeholder={String(sources?.[field.key] || '')}
                      value={values[field.key] ?? ''}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                    />
                    <Button
                      size="icon-sm"
                      variant="ghost"
                      className="h-7 w-7"
                      aria-label={`Save ${field.label}`}
                      onClick={() => handleSave(field.key)}
                      disabled={updateConfig.isPending}
                    >
                      <Save className="w-3 h-3" />
                    </Button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
