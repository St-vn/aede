'use client'
import React, { useState, useEffect, useMemo } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from '@/components/ui/command'
import { ChevronsUpDown, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Model } from '@/hooks/useModels'

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
  openrouter: 'OpenRouter',
  'google-ai': 'Google AI',
  codex: 'Codex (ACP)',
  'claude-code': 'Claude Code (ACP)',
  gemini: 'Gemini (ACP)',
  agy: 'Antigravity (ACP)',
  cline: 'Cline (ACP)',
  cursor: 'Cursor (ACP)',
  goose: 'Goose (ACP)',
  opencode: 'OpenCode (ACP)',
}

const AUTH_CATEGORIES = Object.entries(PROVIDER_LABELS).map(([value, label]) => ({ value, label }))

interface ModelSuggestion {
  id: string
  label: string
  provider: string
}

const MODEL_SUGGESTIONS: ModelSuggestion[] = [
  { label: "Claude Fable 5", id: "claude-fable-5", provider: "anthropic" },
  { label: 'Claude Opus 4.8', id: 'claude-opus-4-8', provider: 'anthropic' },
  { label: 'Claude Sonnet 4.6', id: 'claude-sonnet-4-6', provider: 'anthropic' },
  { label: 'Claude Haiku 4.5', id: 'claude-haiku-4-5-20251001', provider: 'anthropic' },
  { label: 'GPT-5.5', id: 'gpt-5.5', provider: 'openai' },
  { label: 'GPT-5.5 Pro', id: 'gpt-5.5-pro', provider: 'openai' },
  { label: 'GPT-5.4', id: 'gpt-5.4', provider: 'openai' },
  { label: 'GPT-5.4 Pro', id: 'gpt-5.4-pro', provider: 'openai' },
  { label: 'GPT-5.4 Mini', id: 'gpt-5.4-mini', provider: 'openai' },
  { label: 'GPT-5.4 Nano', id: 'gpt-5.4-nano', provider: 'openai' },
  { label: 'GPT-5.3 Codex', id: 'gpt-5.3-codex', provider: 'openai' },
  { label: 'DeepSeek Chat (V4)', id: 'deepseek-chat', provider: 'deepseek' },
  { label: 'DeepSeek V4 Pro', id: 'deepseek/deepseek-v4-pro', provider: 'deepseek' },
  { label: 'DeepSeek V4 Flash', id: 'deepseek/deepseek-v4-flash', provider: 'deepseek' },
  { label: 'DeepSeek Reasoner', id: 'deepseek-reasoner', provider: 'deepseek' },
  { label: 'OpenRouter Auto', id: 'openrouter/auto', provider: 'openrouter' },
  { label: 'DeepSeek V4 Pro', id: 'deepseek/deepseek-v4-pro', provider: 'openrouter' },
  { label: 'DeepSeek V4 Flash', id: 'deepseek/deepseek-v4-flash', provider: 'openrouter' },
  { label: 'Qwen 3.7 Plus', id: 'qwen/qwen3.7-plus', provider: 'openrouter' },
  { label: 'MiniMax M3', id: 'minimax/minimax-m3', provider: 'openrouter' },
  { label: 'Qwen 3.5 Plus', id: 'qwen/qwen3.5-plus-20260420', provider: 'openrouter' },
  { label: 'MiMo V2 Pro', id: 'xiaomi/mimo-v2-pro', provider: 'openrouter' },
  { label: 'Gemini 3.5 Flash', id: 'gemini-3.5-flash', provider: 'google-ai' },
  { label: 'Gemini 3.1 Flash Lite', id: 'gemini-3.1-flash-lite', provider: 'google-ai' },
  { label: 'Gemini 3.1 Pro Preview', id: 'gemini-3.1-pro-preview', provider: 'google-ai' },
  { label: 'Gemini 2.5 Pro', id: 'gemini-2.5-pro', provider: 'google-ai' },
  { label: 'Gemini 2.5 Flash', id: 'gemini-2.5-flash', provider: 'google-ai' },
  { label: 'Codex', id: 'codex', provider: 'codex' },
  { label: 'Claude Code', id: 'claude-code', provider: 'claude-code' },
  { label: 'Gemini', id: 'gemini', provider: 'gemini' },
  { label: 'Antigravity', id: 'agy', provider: 'agy' },
  { label: 'Cline', id: 'cline', provider: 'cline' },
  { label: 'Cursor', id: 'cursor', provider: 'cursor' },
  { label: 'Goose', id: 'goose', provider: 'goose' },
  { label: 'OpenCode', id: 'opencode', provider: 'opencode' },
]

function autoLabel(modelId: string, provider: string): string {
  if (!modelId || !provider) return ''
  const known = MODEL_SUGGESTIONS.find(s => s.id === modelId && s.provider === provider)
  if (known) return known.label
  const pLabel = PROVIDER_LABELS[provider] || provider
  return `${modelId} (${pLabel})`
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: 'add' | 'edit'
  model?: Model
  onSave: (label: string, id: string, provider: string) => void
  onDelete?: () => void
}

export function ModelFormDialog({ open, onOpenChange, mode, model, onSave, onDelete }: Props) {
  const [modelId, setModelId] = useState('')
  const [provider, setProvider] = useState('')
  const [providerOpen, setProviderOpen] = useState(false)
  const [modelOpen, setModelOpen] = useState(false)

  useEffect(() => {
    if (open) {
      if (mode === 'edit' && model) {
        setModelId(model.id)
        setProvider(model.provider)
      } else {
        setModelId('')
        setProvider('')
      }
    }
  }, [open, mode, model])

  const filteredModels = useMemo(() => {
    return MODEL_SUGGESTIONS.filter(s => !provider || s.provider === provider)
  }, [provider])

  const displayLabel = autoLabel(modelId, provider)

  const handleSave = () => {
    if (!displayLabel || !modelId || !provider) return
    onSave(displayLabel, modelId, provider)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>{mode === 'add' ? 'Add Model' : 'Configure Model'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Provider</label>
            <Popover open={providerOpen} onOpenChange={setProviderOpen}>
              <PopoverTrigger
                render={
                  <Button variant="outline" role="combobox" aria-expanded={providerOpen} className="w-full h-8 justify-between text-xs font-normal">
                    {provider ? PROVIDER_LABELS[provider] ?? provider : <span className="text-muted-foreground">Select provider…</span>}
                    <ChevronsUpDown className="size-3.5 shrink-0 opacity-50" />
                  </Button>
                }
              />
              <PopoverContent className="w-(--anchor-width) p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search provider…" className="h-8" />
                  <CommandList>
                    <CommandEmpty>No provider found</CommandEmpty>
                    <CommandGroup>
                      {AUTH_CATEGORIES.map(p => (
                        <CommandItem
                          key={p.value}
                          value={p.label}
                          onSelect={() => {
                            setProvider(p.value)
                            setProviderOpen(false)
                          }}
                          className="text-xs"
                        >
                          <Check className={cn("size-3.5 mr-2", provider === p.value ? "opacity-100" : "opacity-0")} />
                          {p.label}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Model</label>
            <Popover open={modelOpen} onOpenChange={setModelOpen}>
              <PopoverTrigger
                render={
                  <Button variant="outline" role="combobox" aria-expanded={modelOpen} className="w-full h-8 justify-between text-xs font-normal">
                    {modelId ? modelId : <span className="text-muted-foreground">Select or type a model…</span>}
                    <ChevronsUpDown className="size-3.5 shrink-0 opacity-50" />
                  </Button>
                }
              />
              <PopoverContent className="w-(--anchor-width) p-0" align="start">
                <Command>
                  <CommandInput
                    placeholder="Search model…"
                    className="h-8"
                    value={modelId}
                    onValueChange={setModelId}
                  />
                  <CommandList>
                    <CommandEmpty>
                      {modelId ? (
                        <button
                          className="w-full text-left px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded-sm cursor-pointer"
                          onClick={() => { setModelId(modelId); setModelOpen(false) }}
                        >
                          Use &ldquo;{modelId}&rdquo; as custom model ID
                        </button>
                      ) : (
                        'No models found'
                      )}
                    </CommandEmpty>
                    <CommandGroup>
                      {filteredModels.map(s => (
                        <CommandItem
                          key={s.id}
                          value={s.label}
                          onSelect={() => {
                            setModelId(s.id)
                            setModelOpen(false)
                          }}
                          className="text-xs"
                        >
                          <Check className={cn("size-3.5 mr-2", modelId === s.id ? "opacity-100" : "opacity-0")} />
                          <span>{s.label}</span>
                          <span className="ml-auto text-[10px] text-muted-foreground">{s.id}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Displayed name</label>
            <div className="h-8 flex items-center px-3 rounded-lg border border-input/50 bg-input/20 text-xs text-muted-foreground">
              {displayLabel || <span className="italic">Select provider and model to auto-generate</span>}
            </div>
          </div>

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
              <Button size="sm" className="h-8 text-xs" onClick={handleSave} disabled={!modelId || !provider}>
                {mode === 'add' ? 'Add' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
