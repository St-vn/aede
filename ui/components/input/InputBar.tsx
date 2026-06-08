'use client'
import React, { useState, useRef, useEffect } from 'react'
import { ArrowUp, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ModelSelector } from './ModelSelector'

interface Props {
  onSend: (content: string, model?: string) => void
  disabled: boolean
  defaultModel?: string
}

export function InputBar({ onSend, disabled, defaultModel = 'claude-sonnet-4' }: Props) {
  const [text, setText] = useState('')
  const [model, setModel] = useState(defaultModel)
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
  }

  return (
    <div className="px-4 py-3">
      <div className="rounded-2xl border border-border bg-muted px-4 py-3 flex flex-col gap-2">
        <textarea
          ref={ref}
          aria-label="Message"
          placeholder="Write a message..."
          value={text}
          disabled={disabled}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
          className="min-h-[24px] max-h-[200px] resize-none bg-transparent text-sm focus:outline-none
                     placeholder:text-muted-foreground disabled:opacity-50 w-full"
          rows={1}
        />
        <div className="flex items-center justify-between">
          <Tooltip>
            <TooltipTrigger render={
              <Button variant="ghost" size="icon" className="w-7 h-7" aria-label="Add context" disabled={disabled}>
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
