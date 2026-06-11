'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { ArrowUp, Link } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Popover,
  PopoverContent,
} from '@/components/ui/popover'
import { ModelSelector } from './ModelSelector'
import { AcpConnectChip } from './AcpConnectChip'
import { WorkspaceMentionPicker } from './WorkspaceMentionPicker'
import { ContextButton, type FileAttachment } from './ContextButton'
import { SlashCommandPicker } from './SlashCommandPicker'
import { ImagePreviewBar, type ImageAttachment } from './ImagePreviewBar'
import { FileChipBar } from './FileChipBar'

interface Props {
  onSend: (content: string, model?: string) => void
  disabled: boolean
  defaultModel?: string
  sessionId?: string | null
  projectDir?: string | null
  onOpenSettings?: (tab?: string) => void
  onOpenHelp?: () => void
}

let imageIdCounter = 0
function nextImageId() { return `img-${++imageIdCounter}` }

function buildMessageText(text: string, images: ImageAttachment[]): string {
  if (images.length === 0) return text
  const imageMarkdown = images.map(img => `\n![${img.filename}](${img.dataUrl})`).join('')
  return text + imageMarkdown
}

export function InputBar({ onSend, disabled, defaultModel = 'claude-sonnet-4', sessionId, projectDir, onOpenSettings, onOpenHelp }: Props) {
  const [text, setText] = useState('')
  const [model, setModel] = useState(defaultModel)
  const [mentionOpen, setMentionOpen] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const [slashOpen, setSlashOpen] = useState(false)
  const [slashQuery, setSlashQuery] = useState('')
  const [urlPromptOpen, setUrlPromptOpen] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [imageAttachments, setImageAttachments] = useState<ImageAttachment[]>([])
  const [mentionedFiles, setMentionedFiles] = useState<string[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)
  const urlInputRef = useRef<HTMLInputElement>(null)

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

  const submit = () => {
    const trimmed = text.trim()
    if ((!trimmed && imageAttachments.length === 0) || disabled) return
    const message = buildMessageText(trimmed, imageAttachments)
    onSend(message, model)
    setText('')
    setMentionOpen(false)
    setSlashOpen(false)
    setImageAttachments([])
    setMentionedFiles([])
  }

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
            <ModelSelector currentModel={model} onModelChange={setModel}
              onOpenSettings={onOpenSettings ? () => onOpenSettings('models') : undefined} />
            <AcpConnectChip model={model} />
            <Tooltip>
              <TooltipTrigger render={
                <Button size="icon" className="w-7 h-7" aria-label="Send message"
                  disabled={disabled || (!text.trim() && imageAttachments.length === 0)} onClick={submit}>
                  <ArrowUp className="w-4 h-4" />
                </Button>
              } />
              <TooltipContent>Send</TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>
    </div>
  )
}
