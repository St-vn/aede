'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { ArrowUp, Link, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Popover,
  PopoverContent,
} from '@/components/ui/popover'
import { ModelSelector } from './ModelSelector'
import { ModeSelector } from './ModeSelector'
import { AcpConnectChip } from './AcpConnectChip'
import { WorkspaceMentionPicker } from './WorkspaceMentionPicker'
import { ContextButton, type FileAttachment } from './ContextButton'
import { SlashCommandPicker } from './SlashCommandPicker'
import { ImagePreviewBar, type ImageAttachment } from './ImagePreviewBar'
import { FileChipBar } from './FileChipBar'
import { VoiceButton } from './voice/VoiceButton'
import { VoiceController } from './voice/VoiceController'
import { PermissionGate } from './voice/PermissionGate'
import { useSoulFetch } from './voice/useSoulFetch'
import { transcribe } from './voice/AsrClient'
import { apiFetch } from '@/lib/api'

interface Props {
  onSend: (content: string, model?: string) => void
  disabled: boolean
  isStreaming?: boolean
  onStop?: () => void
  onQueue?: (content: string) => void
  defaultModel?: string
  sessionId?: string | null
  projectDir?: string | null
  onOpenSettings?: (tab?: string) => void
  onOpenHelp?: () => void
  model?: string
  onModelChange?: (model: string) => void
  mode?: string
  onModeChange?: (mode: string) => void
  prefillText?: string
  prefillImages?: ImageAttachment[]
}

let imageIdCounter = 0
function nextImageId() { return `img-${++imageIdCounter}` }

function buildMessageText(text: string, images: ImageAttachment[]): string {
  if (images.length === 0) return text
  const imageMarkdown = images.map(img => `\n![${img.filename}](${img.dataUrl})`).join('')
  return text + imageMarkdown
}

export function InputBar({ onSend, disabled, isStreaming = false, onStop, onQueue, defaultModel = 'claude-sonnet-4', sessionId, projectDir, onOpenSettings, onOpenHelp, model: modelProp, onModelChange: onModelChangeProp, mode: modeProp, onModeChange, prefillText, prefillImages }: Props) {
  const [text, setText] = useState(prefillText ?? '')
  const [modelState, setModelState] = useState(defaultModel)
  const model = modelProp ?? modelState
  const setModel = onModelChangeProp ?? setModelState
  const [mentionOpen, setMentionOpen] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const [slashOpen, setSlashOpen] = useState(false)
  const [slashQuery, setSlashQuery] = useState('')
  const [urlPromptOpen, setUrlPromptOpen] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [imageAttachments, setImageAttachments] = useState<ImageAttachment[]>(prefillImages ?? [])
  const [mentionedFiles, setMentionedFiles] = useState<string[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)
  const urlInputRef = useRef<HTMLInputElement>(null)
  const [permDenied, setPermDenied] = useState(false)
  const { soul } = useSoulFetch()

  // VoiceController for push-to-talk. ASR model comes from config (NOT the chat
  // model); held in a ref so config updates apply without re-creating it.
  const asrModelRef = useRef('whisper-large-v3-turbo')
  const voiceControllerRef = useRef<VoiceController | null>(null)
  useEffect(() => {
    voiceControllerRef.current = new VoiceController({
      getStream: () => navigator.mediaDevices.getUserMedia({ audio: true }),
      transcribe: (blob) => transcribe(blob, asrModelRef.current),
    })
    apiFetch<{ voice_asr_model?: string }>('/api/config')
      .then(cfg => { if (cfg.voice_asr_model) asrModelRef.current = cfg.voice_asr_model })
      .catch(() => {})
    return () => {
      voiceControllerRef.current?.stop()
    }
  }, [])

  // submitRef avoids a stale-closure: the wake controller's onTranscript is
  // created in an effect but must always call the latest submit().
  const submitRef = useRef<(override?: string) => void>(() => {})

  // VoiceController for the always-on wake word. Armed only when a wake word is
  // configured. On transcript → submit (auto-send), distinct from push-to-talk
  // which inserts at cursor.
  const wakeControllerRef = useRef<VoiceController | null>(null)
  useEffect(() => {
    if (!soul?.wake_word) return
    let vc: VoiceController | null = null
    let disposed = false
    // Read voice settings (ASR + wake model) from config, then arm.
    apiFetch<{ voice_asr_model?: string; voice_wake_model?: string; voice_wake_word_enabled?: boolean }>('/api/config')
      .then(cfg => {
        if (disposed || cfg.voice_wake_word_enabled === false) return
        const asrModel = cfg.voice_asr_model ?? 'whisper-large-v3-turbo'
        const wakeKeyword = cfg.voice_wake_model ?? 'hey_jarvis'
        vc = new VoiceController({
          getStream: () => navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true } }),
          transcribe: (blob) => transcribe(blob, asrModel),  // ASR model, NOT the chat model
          onTranscript: (txt) => { if (txt.trim()) submitRef.current(txt) },
          createWake: async (opts) => {
            const { createWakeWordEngine } = await import('./voice/wakeWorklet')
            return createWakeWordEngine(opts)
          },
          wakeOpts: { keywords: [wakeKeyword] },
        })
        wakeControllerRef.current = vc
        // Lazy-arm: load WASM + models only now that voice is enabled.
        void vc.start().catch(() => { /* permission/load failure is non-fatal */ })
      })
      .catch(() => { /* config fetch failure → wake stays disarmed */ })
    return () => {
      disposed = true
      vc?.stop()
      wakeControllerRef.current = null
    }
  }, [soul?.wake_word])

  // Auto-resize
  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = 'auto'
      ref.current.style.height = `${Math.min(ref.current.scrollHeight, 200)}px`
    }
  }, [text])

  // Focus URL input when prompt opens
  useEffect(() => {
    if (urlPromptOpen && urlInputRef.current) {
      urlInputRef.current.focus()
    }
  }, [urlPromptOpen])

  const submit = (override?: string) => {
    const trimmed = (override ?? text).trim()
    if ((!trimmed && imageAttachments.length === 0) || disabled) return
    const message = buildMessageText(trimmed, imageAttachments)
    if (isStreaming) {
      onQueue?.(message)
      setText('')
      setMentionOpen(false)
      setSlashOpen(false)
      setImageAttachments([])
      setMentionedFiles([])
      return
    }
    onSend(message, model)
    setText('')
    setMentionOpen(false)
    setSlashOpen(false)
    setImageAttachments([])
    setMentionedFiles([])
  }
  submitRef.current = submit

  // --- File injection ---
  const injectFiles = useCallback((files: FileAttachment[]) => {
    if (!ref.current) return
    const cursor = ref.current.selectionStart
    const blocks = files.map(f => `\`\`\`${f.filename}\n${f.content}\n\`\`\``).join('\n')
    const before = text.slice(0, cursor)
    const after = text.slice(ref.current.selectionEnd)
    const newText = before + blocks + (after ? '\n' + after : '')
    setText(newText)
    setTimeout(() => {
      if (ref.current) {
        ref.current.focus()
        ref.current.setSelectionRange(before.length + blocks.length, before.length + blocks.length)
      }
    }, 0)
  }, [text])

  // --- Image handling ---
  const addImageAttachment = useCallback((blob: Blob) => {
    const reader = new FileReader()
    reader.onload = () => {
      const id = nextImageId()
      const ext = blob.type.split('/')[1] || 'png'
      setImageAttachments(prev => [...prev, {
        id,
        dataUrl: reader.result as string,
        mime: blob.type,
        filename: `pasted-image-${id}.${ext}`,
      }])
    }
    reader.readAsDataURL(blob)
  }, [])

  // --- Drag and drop ---
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!isDragging) setIsDragging(true)
  }, [isDragging])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length === 0) return

    const textFiles: FileAttachment[] = []
    for (const file of files) {
      if (file.type.startsWith('image/')) {
        addImageAttachment(file)
      } else {
        const content = await file.text()
        textFiles.push({ filename: file.name, content })
      }
    }
    if (textFiles.length > 0) injectFiles(textFiles)
  }, [addImageAttachment, injectFiles])

  const removeImage = useCallback((id: string) => {
    setImageAttachments(prev => prev.filter(img => img.id !== id))
  }, [])

  const hasPastedImage = useCallback((items: DataTransferItemList): boolean => {
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item?.kind === 'file' && item.type.startsWith('image/')) {
        const blob = item.getAsFile()
        if (blob) addImageAttachment(blob)
        return true
      }
    }
    return false
  }, [addImageAttachment])

  const hasClipboardImage = useCallback(async (items: ClipboardItems): Promise<boolean> => {
    for (const item of items) {
      for (const type of item.types) {
        if (type.startsWith('image/')) {
          const blob = await item.getType(type)
          addImageAttachment(blob)
          return true
        }
      }
    }
    return false
  }, [addImageAttachment])

  // --- Paste handler (Ctrl+V) ---
  const handlePaste = useCallback(async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const foundImage = hasPastedImage(e.clipboardData.items)
    if (foundImage) e.preventDefault()
  }, [hasPastedImage])

  // --- Paste from clipboard button ---
  const handlePasteFromClipboard = useCallback(async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.read) {
        const items = await navigator.clipboard.read()
        const foundImage = await hasClipboardImage(items)
        if (foundImage) return
      }
      const clipboardText = await navigator.clipboard.readText()
      if (clipboardText) {
        const quoted = clipboardText.split('\n').map(l => `> ${l}`).join('\n')
        setText(prev => prev ? prev + '\n' + quoted : quoted)
      }
    } catch {
      // clipboard access denied or unavailable
    }
  }, [hasClipboardImage])

  // --- Add URL ---
  const handleAddUrl = useCallback(() => {
    setUrlInput('')
    setUrlPromptOpen(true)
  }, [])

  const handleUrlSubmit = useCallback(() => {
    const trimmed = urlInput.trim()
    if (trimmed) {
      setText(prev => prev ? prev + '\n' + trimmed : trimmed)
    }
    setUrlPromptOpen(false)
    setUrlInput('')
    setTimeout(() => ref.current?.focus(), 0)
  }, [urlInput])

  // --- Slash command ---
  const handleSlashSelect = useCallback((command: string) => {
    if (command === '/settings') {
      onOpenSettings?.()
      setSlashOpen(false)
      setSlashQuery('')
      return
    }
    if (command.startsWith('/settings:')) {
      const tab = command.split(':')[1]
      onOpenSettings?.(tab)
      setSlashOpen(false)
      setSlashQuery('')
      return
    }
    if (command === '/help') {
      onOpenHelp?.()
      setSlashOpen(false)
      setSlashQuery('')
      return
    }
    // Regular command - insert text
    setText(command)
    setSlashOpen(false)
    setSlashQuery('')
    setTimeout(() => ref.current?.focus(), 0)
  }, [onOpenSettings, onOpenHelp])

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setText(val)

    // Check for @ mention
    const cursor = e.target.selectionStart
    const lastAtIdx = val.lastIndexOf('@', cursor - 1)
    if (lastAtIdx !== -1) {
      const isStart = lastAtIdx === 0
      const hasPrecedingSpace = val.charAt(lastAtIdx - 1) === ' ' || val.charAt(lastAtIdx - 1) === '\n'
      if (isStart || hasPrecedingSpace) {
        const query = val.slice(lastAtIdx + 1, cursor)
        if (!query.includes(' ')) {
          setMentionOpen(true)
          setMentionQuery(query)
          return
        }
      }
    }
    setMentionOpen(false)

    // Slash picker: close if text no longer starts with /
    if (slashOpen && !val.startsWith('/')) {
      setSlashOpen(false)
      setSlashQuery('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Slash command trigger: "/" at position 0 with empty or whitespace-only input
    if (e.key === '/' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
      if (ref.current && ref.current.selectionStart === 0 && !text.trim()) {
        setSlashOpen(true)
        setSlashQuery('')
        return
      }
    }

    // Submit on Enter (not Shift+Enter, not when slash picker is open)
    if (e.key === 'Enter' && !e.shiftKey && !mentionOpen && !slashOpen) {
      e.preventDefault()
      submit()
    }
  }

  const handleSelectMention = (file: string) => {
    if (!ref.current) return
    const cursor = ref.current.selectionStart
    const val = text
    const lastAtIdx = val.lastIndexOf('@', cursor - 1)
    if (lastAtIdx !== -1) {
      const before = val.slice(0, lastAtIdx)
      const after = val.slice(cursor)
      const replacement = `@[${file}] `
      const newText = before + replacement + after
      setText(newText)
      setMentionOpen(false)
      setMentionedFiles(prev => [...prev, file])
      setTimeout(() => {
        if (ref.current) {
          ref.current.focus()
          ref.current.setSelectionRange(lastAtIdx + replacement.length, lastAtIdx + replacement.length)
        }
      }, 0)
    }
  }

  const handleRemoveMentionedFile = useCallback((filename: string) => {
    const pattern = `@[${filename}] `
    const newText = text.replace(pattern, '')
    setText(newText)
    setMentionedFiles(prev => prev.filter(f => f !== filename))
  }, [text])

  // Sync mentionedFiles from text content
  useEffect(() => {
    const mentioned = text.match(/@\[([^\]]+)\]/g) || []
    const names = mentioned.map(m => m.slice(2, -1))
    setMentionedFiles(prev => prev.filter(f => names.includes(f)))
  }, [text])

  // Track text changes for slash query updates
  useEffect(() => {
    if (slashOpen && text.startsWith('/')) {
      setSlashQuery(text.slice(1))
    }
  }, [text, slashOpen])

  return (
    <div className="px-4 py-3 relative">
      <WorkspaceMentionPicker
        open={mentionOpen}
        onOpenChange={setMentionOpen}
        onSelect={handleSelectMention}
        searchQuery={mentionQuery}
        triggerRef={ref}
        sessionId={sessionId}
        projectDir={projectDir}
      />
      <SlashCommandPicker
        open={slashOpen}
        onOpenChange={setSlashOpen}
        onSelect={handleSlashSelect}
        searchQuery={slashQuery}
        triggerRef={ref}
      />
      <Popover open={urlPromptOpen} onOpenChange={setUrlPromptOpen}>
        <PopoverContent
          className="w-[280px] p-3"
          align="start"
          side="top"
          sideOffset={8}
          initialFocus={false}
          anchor={ref}
        >
          <div className="flex items-center gap-2">
            <Link className="w-4 h-4 text-muted-foreground shrink-0" />
            <input
              ref={urlInputRef}
              type="url"
              placeholder="Enter a URL..."
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') handleUrlSubmit()
                if (e.key === 'Escape') setUrlPromptOpen(false)
              }}
              className="flex-1 bg-transparent text-sm border-b border-border outline-none
                         placeholder:text-muted-foreground/50 focus:border-primary"
            />
            <Button size="sm" className="h-7 text-xs" onClick={handleUrlSubmit}>Add</Button>
          </div>
        </PopoverContent>
      </Popover>
      <div
        className="rounded-2xl border border-border bg-muted px-4 py-3 flex flex-col gap-2 relative"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {isDragging && (
          <div className="absolute inset-0 rounded-2xl border-2 border-dashed border-primary/50 bg-primary/5 z-10
                          flex items-center justify-center text-sm text-muted-foreground pointer-events-none">
            Drop files here to attach
          </div>
        )}
        <ImagePreviewBar images={imageAttachments} onRemove={removeImage} />
        <FileChipBar files={mentionedFiles} onRemove={handleRemoveMentionedFile} />
        <PermissionGate showing={permDenied} onDismiss={() => setPermDenied(false)} />
        <textarea
          ref={ref}
          aria-label="Message"
          placeholder="Write a message... Use @ to mention files."
          value={text}
          disabled={disabled}
          onChange={handleInputChange}
          onPaste={handlePaste}
          onKeyDown={handleKeyDown}
          className="min-h-[24px] max-h-[200px] resize-none bg-transparent text-sm focus:outline-none
                     placeholder:text-muted-foreground disabled:opacity-50 w-full"
          rows={1}
        />
        <div className="flex items-center justify-between">
          <ContextButton
            disabled={disabled}
            onAttachFile={injectFiles}
            onPasteFromClipboard={handlePasteFromClipboard}
            onAddUrl={handleAddUrl}
          />
          <div className="flex items-center gap-2">
            {onModeChange && (
              <ModeSelector currentMode={modeProp ?? 'normal'} onModeChange={onModeChange} />
            )}
            <ModelSelector currentModel={model} onModelChange={setModel}
              onOpenSettings={onOpenSettings ? () => onOpenSettings('models') : undefined} />
            <AcpConnectChip model={model} />
            <VoiceButton
              enabled={true}
              captureOnce={() => voiceControllerRef.current?.captureOnce() ?? Promise.resolve('')}
              textareaRef={ref}
              setText={setText}
              onPermissionDenied={() => setPermDenied(true)}
              onError={() => {}}
            />
            {isStreaming ? (
              <div className="flex items-center gap-1.5">
                <Button size="icon" className="w-7 h-7" variant="destructive"
                  aria-label="Stop generating" onClick={onStop}>
                  <Square className="w-4 h-4 fill-current" />
                </Button>
                <Tooltip>
                  <TooltipTrigger render={
                    <Button size="icon" className="w-7 h-7" variant="ghost"
                      aria-label="Send queued message"
                      disabled={!text.trim() && imageAttachments.length === 0}
                      onClick={() => submit()}>
                      <ArrowUp className="w-4 h-4" />
                    </Button>
                  } />
                  <TooltipContent>Will queue until current turn ends</TooltipContent>
                </Tooltip>
              </div>
            ) : (
              <Tooltip>
                <TooltipTrigger render={
                  <Button size="icon" className="w-7 h-7" aria-label="Send message"
                    disabled={disabled || (!text.trim() && imageAttachments.length === 0)} onClick={() => submit()}>
                    <ArrowUp className="w-4 h-4" />
                  </Button>
                } />
                <TooltipContent>Send</TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
