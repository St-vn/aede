'use client'
import React, { useState } from 'react'
import { Brain, ChevronDown } from 'lucide-react'

interface Props {
  thinking: string
  isStreaming: boolean
}

export function ThinkingBlock({ thinking, isStreaming }: Props) {
  const [isOpen, setIsOpen] = useState(false)

  if (!thinking) return null

  const charCount = thinking.length

  return (
    <div className="border border-border rounded-lg my-2 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full px-3 py-2 text-xs text-muted-foreground
                   hover:text-foreground hover:bg-muted/50 transition-colors"
      >
        <Brain className="w-3.5 h-3.5 shrink-0" />
        <span className="font-medium">Reasoning</span>
        <span className="text-[10px] text-muted-foreground/60">{charCount} chars</span>
        {isStreaming && (
          <span className="inline-block w-2 h-2 rounded-full bg-yellow-500 animate-pulse ml-auto" />
        )}
        <ChevronDown className={`w-3.5 h-3.5 ml-auto transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div className="px-3 pb-2 max-h-[300px] overflow-y-auto">
          <pre className="text-xs text-muted-foreground font-mono whitespace-pre-wrap leading-relaxed">
            {thinking}
          </pre>
        </div>
      )}
    </div>
  )
}
