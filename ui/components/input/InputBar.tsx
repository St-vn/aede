'use client'
import React, { useState, useRef, useEffect } from 'react'
import { ArrowUp, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ModelSelector } from './ModelSelector'
import { WorkspaceMentionPicker } from './WorkspaceMentionPicker'

interface Props {
  onSend: (content: string, model?: string) => void
  disabled: boolean
  defaultModel?: string
  sessionId?: string | null
}

export function InputBar({ onSend, disabled, defaultModel = 'claude-sonnet-4', sessionId }: Props) {
  const [text, setText] = useState('')
  const [model, setModel] = useState(defaultModel)
  const [mentionOpen, setMentionOpen] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  // Auto-resize
  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = 'auto'
      ref.current.style.height = `${Math.min(ref.current.scrollHeight, 200)}px`
    }
  }, [text])

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed, model)
    setText('')
    setMentionOpen(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setText(val)
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
      setTimeout(() => {
        if (ref.current) {
          ref.current.focus()
          ref.current.setSelectionRange(lastAtIdx + replacement.length, lastAtIdx + replacement.length)
        }
      }, 0)
    }
  }

  return (
    <div className="px-4 py-3 relative">
      <WorkspaceMentionPicker
        open={mentionOpen}
        onOpenChange={setMentionOpen}
        onSelect={handleSelectMention}
        searchQuery={mentionQuery}
        triggerRef={ref}
        sessionId={sessionId}
      />
      <div className="rounded-2xl border border-border bg-muted px-4 py-3 flex flex-col gap-2">
        <textarea
          ref={ref}
          aria-label="Message"
          placeholder="Write a message... Use @ to mention files."
          value={text}
          disabled={disabled}
          onChange={handleInputChange}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && !mentionOpen) {
              e.preventDefault()
              submit()
            }
          }}
          className="min-h-[24px] max-h-[200px] resize-none bg-transparent text-sm focus:outline-none
                     placeholder:text-muted-foreground disabled:opacity-50 w-full"
          rows={1}
        />
        <div className="flex items-center justify-between">
          <Tooltip>
            <TooltipTrigger render={
              <Button variant="ghost" size="icon" className="w-7 h-7" aria-label="Add context" disabled={disabled} onClick={() => {
                setText(prev => prev + '@')
                setMentionOpen(true)
                setMentionQuery('')
                ref.current?.focus()
              }}>
                <Plus className="w-4 h-4" />
              </Button>
            } />
            <TooltipContent>Add context</TooltipContent>
          </Tooltip>
          <div className="flex items-center gap-2">
            <ModelSelector currentModel={model} onModelChange={setModel} />
            <Tooltip>
              <TooltipTrigger render={
                <Button size="icon" className="w-7 h-7" aria-label="Send message"
                  disabled={disabled || !text.trim()} onClick={submit}>
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
