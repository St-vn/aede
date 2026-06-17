'use client'
import React from 'react'
import { Brain, Check, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu'
import { useModels } from '@/hooks/useModels'
import { useConfig, useUpdateConfig } from '@/hooks/useConfig'

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  openrouter: 'OpenRouter',
  'google-ai': 'Google AI',
  codex: 'Codex',
  'claude-code': 'Claude Code',
  gemini: 'Gemini',
  agy: 'Antigravity',
  cline: 'Cline',
  cursor: 'Cursor',
  goose: 'Goose',
  'opencode-zen': 'OpenCode Zen',
  'opencode-go': 'OpenCode Go',
}

interface EffortOption { value: string; label: string }

function getEffortOptions(modelId: string, provider: string): EffortOption[] {
  if (provider === 'anthropic' || modelId.startsWith('claude-')) {
    if (modelId.includes('opus-4')) {
      return [
        { value: 'auto', label: 'Auto' },
        { value: 'low', label: 'Low' },
        { value: 'medium', label: 'Medium' },
        { value: 'high', label: 'High' },
        { value: 'xhigh', label: 'XHigh' },
        { value: 'max', label: 'Max' },
      ]
    }
    if (modelId.includes('sonnet-4')) {
      return [
        { value: 'auto', label: 'Auto' },
        { value: 'none', label: 'None' },
      ]
    }
    return []
  }

  if (provider === 'openai') {
    return [
      { value: 'auto', label: 'Auto' },
      { value: 'none', label: 'None' },
      { value: 'minimal', label: 'Minimal' },
      { value: 'low', label: 'Low' },
      { value: 'medium', label: 'Medium' },
      { value: 'high', label: 'High' },
      { value: 'xhigh', label: 'XHigh' },
    ]
  }

  if (provider === 'deepseek' || modelId.startsWith('deepseek-')) {
    return [
      { value: 'auto', label: 'Auto' },
      { value: 'none', label: 'None' },
      { value: 'high', label: 'High' },
      { value: 'max', label: 'Max' },
    ]
  }

  if (provider === 'google-ai' || provider === 'gemini' || modelId.startsWith('gemini-')) {
    if (modelId.includes('2.5')) {
      return [
        { value: 'auto', label: 'Auto' },
        { value: 'minimal', label: 'Minimal' },
        { value: 'low', label: 'Low' },
        { value: 'medium', label: 'Medium' },
        { value: 'high', label: 'High' },
      ]
    }
    return []
  }

  if (provider === 'openrouter') {
    return [
      { value: 'auto', label: 'Auto' },
      { value: 'low', label: 'Low' },
      { value: 'medium', label: 'Medium' },
      { value: 'high', label: 'High' },
    ]
  }

  return []
}

interface Props { currentModel: string; onModelChange: (m: string) => void; onOpenSettings?: () => void }

export function ModelSelector({ currentModel, onModelChange, onOpenSettings }: Props) {
  const { data: models = [] } = useModels()
  const { data: config } = useConfig()
  const updateConfig = useUpdateConfig()

  const [localEffort, setLocalEffort] = React.useState('auto')
  const [localThinking, setLocalThinking] = React.useState(false)

  React.useEffect(() => {
    if (config?.reasoning_effort) {
      setLocalEffort(config.reasoning_effort)
    }
  }, [config?.reasoning_effort])

  React.useEffect(() => {
    setLocalThinking((config?.thinking_budget ?? 0) > 0)
  }, [config?.thinking_budget])

  const groupedModels: Record<string, typeof models> = {}
  for (const m of models) {
    (groupedModels[m.provider] ??= []).push(m)
  }

  const current = models.find(m => m.id === currentModel) ?? { id: currentModel, label: currentModel, provider: '' }

  const effortOptions = getEffortOptions(currentModel, current.provider)
  const effortLabel = effortOptions.find(o => o.value === localEffort)?.label || localEffort

  const handleSelect = (id: string) => {
    onModelChange(id)
    updateConfig.mutate({ key: 'model', value: id, scope: 'global' })
  }

  const handleEffortChange = (value: string) => {
    setLocalEffort(value)
    updateConfig.mutate({ key: 'reasoning_effort', value, scope: 'global' })
  }

  const handleThinkingChange = (on: boolean) => {
    setLocalThinking(on)
    updateConfig.mutate({ key: 'thinking_budget', value: on ? '4096' : '0', scope: 'global' })
  }

  const providers = Object.keys(groupedModels)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={
        <Button variant="ghost" size="sm" aria-label="Select model" className="text-xs text-muted-foreground gap-1 max-w-[120px] truncate">
          {current.label}
        </Button>
      } />
      <DropdownMenuContent align="end" className="min-w-[200px]">
          <div className="max-h-[250px] overflow-y-auto scroll-thin">
            {providers.map(provider => (
              <DropdownMenuGroup key={provider}>
                <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {PROVIDER_LABELS[provider] || provider}
                </DropdownMenuLabel>
                {groupedModels[provider].map(m => (
                  <DropdownMenuItem key={m.id} onClick={() => handleSelect(m.id)} className="text-xs">
                    {m.id === currentModel && <Check className="w-3 h-3 mr-2 shrink-0" />}
                    <span className={m.id !== currentModel ? 'ml-5' : ''}>{m.label}</span>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuGroup>
            ))}
          </div>
        {effortOptions.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuSub>
              <DropdownMenuSubTrigger className="text-xs gap-2">
                <span>Reasoning</span>
                <span className="text-muted-foreground ml-auto">{effortLabel}</span>
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent className="min-w-[100px]">
                <DropdownMenuRadioGroup value={localEffort} onValueChange={handleEffortChange}>
                  {effortOptions.map(opt => (
                    <DropdownMenuRadioItem key={opt.value} value={opt.value} className="text-xs">
                      {opt.label}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuRadioGroup>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="text-xs gap-2">
            <Brain className="w-3 h-3" />
            <span>Thinking</span>
            <span className="text-muted-foreground ml-auto">{localThinking ? 'On (4k)' : 'Off'}</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent className="min-w-[100px]">
            <DropdownMenuRadioGroup value={localThinking ? 'on' : 'off'} onValueChange={(v) => handleThinkingChange(v === 'on')}>
              <DropdownMenuRadioItem value="off" className="text-xs">Off</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="on" className="text-xs">On (4k)</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onOpenSettings} className="text-xs text-muted-foreground">
          <Settings className="w-3 h-3 mr-2" />
          More models...
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
