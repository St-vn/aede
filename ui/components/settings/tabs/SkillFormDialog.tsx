'use client'
import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormModal } from '@/components/ui/form-modal'
import { apiFetch } from '@/lib/api'
import type { SkillInfo } from '@/hooks/useSkills'
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
  skill?: SkillInfo
  scope?: string
  projectDir?: string
  onSave: (data: Record<string, unknown>) => void
  onDelete?: () => void
}

export function SkillFormDialog({ open, onOpenChange, mode, skill, scope, projectDir, onSave, onDelete }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [triggerPhrases, setTriggerPhrases] = useState('')
  const [allowedTools, setAllowedTools] = useState<string[]>([])
  const [model, setModel] = useState('')
  const [body, setBody] = useState('')

  useEffect(() => {
    if (open) {
      if (mode === 'edit' && skill) {
        setName(skill.name)
        setDescription(skill.description)
        setTriggerPhrases((skill.trigger_phrases || []).join(', '))
        setAllowedTools(skill.allowed_tools || [])
        setModel(skill.model || '')
        setBody(skill.body || '')
      } else {
        setName('')
        setDescription('')
        setTriggerPhrases('')
        setAllowedTools([])
        setModel('')
        setBody('')
      }
    }
  }, [open, mode, skill])

  const handleSave = () => {
    if (!name.trim() || !description.trim()) return
    const data: Record<string, unknown> = {
      name: name.trim(),
      description: description.trim(),
      trigger_phrases: triggerPhrases.trim() ? triggerPhrases.split(',').map(s => s.trim()).filter(Boolean) : [],
      allowed_tools: allowedTools,
      model: model.trim() || null,
      body,
    }
    onSave(data)
    onOpenChange(false)
  }

  return (
    <FormModal open={open} onOpenChange={onOpenChange} title={mode === 'add' ? 'Add Skill' : 'Edit Skill'}
      filePath={mode === 'edit' ? skill?.file_path : undefined}
      onOpenFile={mode === 'edit' && skill ? () => apiFetch(`/api/skills/${encodeURIComponent(skill.name)}/open?scope=${scope || 'global'}${projectDir ? `&project_dir=${encodeURIComponent(projectDir)}` : ''}`, { method: 'POST' }) : undefined}>
      <div className="space-y-3">
          <Field label="Name">
            <Input value={name} onChange={e => setName(e.target.value)} className="h-8 text-xs" placeholder="my-skill" disabled={mode === 'edit'} />
          </Field>
          <Field label="Description">
            <Input value={description} onChange={e => setDescription(e.target.value)} className="h-8 text-xs" placeholder="What this skill does" />
          </Field>
          <Field label="Trigger phrases (comma-separated)">
            <Input value={triggerPhrases} onChange={e => setTriggerPhrases(e.target.value)} className="h-8 text-xs" placeholder="research, find info, look up" />
          </Field>
          {/* <Field label="Allowed tools (blank = all)">
            <ChipSelect value={allowedTools} onChange={setAllowedTools} options={useTools} label="tool" />
          </Field> */}
          {/* <Field label="Model (blank = inherit)">
            <ModelDropdown model={model} onModelChange={setModel} />
          </Field> */}
          <Field label="Body">
            <Textarea value={body} onChange={e => setBody(e.target.value)} className="text-xs min-h-[80px]" placeholder="Skill instruction content" />
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
            <DropdownMenuItem onClick={() => { onModelChange(''); setShowCustom(false) }} className="text-xs">
              {model === '' && <Check className="w-3 h-3 mr-2 shrink-0" />}
              <span className={model !== '' ? 'ml-5' : ''}>inherit</span>
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
          onKeyDown={e => { if (e.key === 'Enter') { onModelChange(customValue.trim() || ''); setShowCustom(false) } }}
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
