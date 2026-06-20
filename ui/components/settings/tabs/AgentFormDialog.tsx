'use client'
import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormModal } from '@/components/ui/form-modal'
import { apiFetch } from '@/lib/api'
import type { AgentInfo } from '@/hooks/useAgents'
import { useSkills } from '@/hooks/useSkills'
import { useTools } from '@/hooks/useTools'
import { useModels } from '@/hooks/useModels'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuGroup, DropdownMenuLabel, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem,
} from '@/components/ui/command'
import { X, Plus, Check, ChevronDown } from 'lucide-react'

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

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: 'add' | 'edit'
  agent?: AgentInfo
  scope?: string
  projectDir?: string
  onSave: (data: Record<string, unknown>) => void
  onDelete?: () => void
}

export function AgentFormDialog({ open, onOpenChange, mode, agent, scope, projectDir, onSave, onDelete }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [model, setModel] = useState('inherit')
  const [skills, setSkills] = useState<string[]>([])
  const [tools, setTools] = useState<string[]>([])
  const [disallowedTools, setDisallowedTools] = useState<string[]>([])
  const [maxTurns, setMaxTurns] = useState('20')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [body, setBody] = useState('')

  useEffect(() => {
    if (open) {
      if (mode === 'edit' && agent) {
        setName(agent.name)
        setDescription(agent.description)
        setModel(agent.model || 'inherit')
        setSkills(agent.skills || [])
        setTools(agent.tools || [])
        setDisallowedTools(agent.disallowed_tools || [])
        setMaxTurns(String(agent.max_turns ?? 20))
        setSystemPrompt(agent.system_prompt || '')
        setBody(agent.body || '')
      } else {
        setName('')
        setDescription('')
        setModel('inherit')
        setSkills([])
        setTools([])
        setDisallowedTools([])
        setMaxTurns('20')
        setSystemPrompt('')
        setBody('')
      }
    }
  }, [open, mode, agent])

  const handleSave = () => {
    if (!name.trim() || !description.trim()) return
    const data: Record<string, unknown> = {
      name: name.trim(),
      description: description.trim(),
      model: model.trim() || 'inherit',
      skills,
      tools,
      disallowed_tools: disallowedTools,
      max_turns: parseInt(maxTurns) || 20,
      system_prompt: systemPrompt,
      body,
    }
    onSave(data)
    onOpenChange(false)
  }

  return (
    <FormModal open={open} onOpenChange={onOpenChange} title={mode === 'add' ? 'Add Agent' : 'Edit Agent'}
      filePath={mode === 'edit' ? agent?.file_path : undefined}
      onOpenFile={mode === 'edit' && agent ? () => apiFetch(`/api/agents/${encodeURIComponent(agent.name)}/open?scope=${scope || 'global'}${projectDir ? `&project_dir=${encodeURIComponent(projectDir)}` : ''}`, { method: 'POST' }) : undefined}>
      <div className="space-y-3">
          <Field label="Name">
            <Input value={name} onChange={e => setName(e.target.value)} className="h-8 text-xs" placeholder="my-agent" disabled={mode === 'edit'} />
          </Field>
          <Field label="Description">
            <Input value={description} onChange={e => setDescription(e.target.value)} className="h-8 text-xs" placeholder="What this agent does" />
          </Field>
          <Field label="Model">
            <ModelDropdown model={model} onModelChange={setModel} />
          </Field>
          <Field label="Skills">
            <ChipSelect value={skills} onChange={setSkills} options={useSkills} label="skill" />
          </Field>
          <Field label="Allowed tools (blank = all)">
            <ChipSelect value={tools} onChange={setTools} options={useTools} label="tool" />
          </Field>
          <Field label="Disallowed tools">
            <ChipSelect value={disallowedTools} onChange={setDisallowedTools} options={useTools} label="tool" />
          </Field>
          <Field label="Max turns">
            <Input value={maxTurns} onChange={e => setMaxTurns(e.target.value)} className="h-8 text-xs" placeholder="20" type="number" min={1} />
          </Field>
          <Field label="System prompt">
            <Textarea value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} className="text-xs min-h-[60px]" placeholder="Custom system prompt for this agent" />
          </Field>
          <Field label="Body">
            <Textarea value={body} onChange={e => setBody(e.target.value)} className="text-xs min-h-[80px]" placeholder="Additional body text after frontmatter" />
          </Field>
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
              <Button size="sm" className="h-8 text-xs" onClick={handleSave} disabled={!name.trim() || !description.trim()}>
                {mode === 'add' ? 'Create' : 'Save'}
              </Button>
            </div>
          </div>
        </div>
    </FormModal>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  )
}

function ModelDropdown({ model, onModelChange }: { model: string; onModelChange: (m: string) => void }) {
  const { data: models = [] } = useModels()
  const [customValue, setCustomValue] = useState('')
  const [showCustom, setShowCustom] = useState(false)

  const groupedModels: Record<string, typeof models> = {}
  for (const m of models) {
    (groupedModels[m.provider] ??= []).push(m)
  }

  const providers = Object.keys(groupedModels)

  const isPreset = models.some(m => m.id === model)

  return (
    <div className="flex items-center gap-1">
      <DropdownMenu>
        <DropdownMenuTrigger render={
          <Button variant="outline" className="h-8 text-xs justify-between min-w-[140px]">
            <span className="truncate">{isPreset ? (models.find(m => m.id === model)?.label ?? model) : model || 'inherit'}</span>
            <ChevronDown className="w-3 h-3 ml-1 shrink-0" />
          </Button>
        } />
        <DropdownMenuContent align="start" className="min-w-[200px]">
          <div className="max-h-[250px] overflow-y-auto scroll-thin">
            <DropdownMenuItem onClick={() => { onModelChange('inherit'); setShowCustom(false) }} className="text-xs">
              {model === 'inherit' && <Check className="w-3 h-3 mr-2 shrink-0" />}
              <span className={model !== 'inherit' ? 'ml-5' : ''}>inherit</span>
            </DropdownMenuItem>
            {providers.map(provider => (
              <DropdownMenuGroup key={provider}>
                <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {PROVIDER_LABELS[provider] || provider}
                </DropdownMenuLabel>
                {groupedModels[provider].map(m => (
                  <DropdownMenuItem key={m.id} onClick={() => { onModelChange(m.id); setShowCustom(false) }} className="text-xs">
                    {m.id === model && <Check className="w-3 h-3 mr-2 shrink-0" />}
                    <span className={m.id !== model ? 'ml-5' : ''}>{m.label}</span>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuGroup>
            ))}
          </div>
          <DropdownMenuItem onClick={() => setShowCustom(!showCustom)} className="text-xs text-muted-foreground">
            Custom model ID...
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {showCustom && (
        <Input
          value={customValue}
          onChange={e => { setCustomValue(e.target.value); onModelChange(e.target.value) }}
          onBlur={() => { if (!customValue.trim()) setShowCustom(false) }}
          onKeyDown={e => { if (e.key === 'Enter') { onModelChange(customValue.trim() || 'inherit'); setShowCustom(false) } }}
          className="h-8 text-xs w-[120px]"
          placeholder="model-id"
          autoFocus
        />
      )}
    </div>
  )
}

function ChipSelect({ value, onChange, options: useOptionsHook, label }: {
  value: string[]
  onChange: (v: string[]) => void
  options: () => { data?: { name: string }[] }
  label: string
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const { data: allOptions = [] } = useOptionsHook()

  const filtered = allOptions.filter(o =>
    o.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="border rounded-md p-1.5 min-h-[32px]">
      <div className="flex flex-wrap gap-1">
        {value.map(name => (
          <span key={name} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-muted text-xs">
            {name}
            <button
              type="button"
              onClick={() => onChange(value.filter(v => v !== name))}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        {value.length === 0 && <span className="text-xs text-muted-foreground">None selected</span>}
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger render={
            <button type="button" className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border border-dashed text-xs text-muted-foreground hover:text-foreground hover:border-foreground/50">
              <Plus className="w-3 h-3" />
            </button>
          } />
          <PopoverContent className="w-[220px] p-0" align="start">
            <Command>
              <CommandInput
                value={search}
                onValueChange={setSearch}
                placeholder={`Search ${label}s...`}
                className="h-8 text-xs"
              />
              <CommandList>
                <CommandEmpty className="text-xs">No {label}s found.</CommandEmpty>
                <CommandGroup>
                  {filtered.map(opt => {
                    const selected = value.includes(opt.name)
                    return (
                      <CommandItem
                        key={opt.name}
                        value={opt.name}
                        onSelect={() => {
                          onChange(selected ? value.filter(v => v !== opt.name) : [...value, opt.name])
                          setSearch('')
                        }}
                        className="text-xs"
                      >
                        <Check className={`w-3 h-3 mr-2 shrink-0 ${selected ? 'opacity-100' : 'opacity-0'}`} />
                        {opt.name}
                      </CommandItem>
                    )
                  })}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      </div>
    </div>
  )
}
