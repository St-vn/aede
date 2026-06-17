'use client'
import React from 'react'
import { CollapsibleBlock } from './CollapsibleBlock'

interface Props {
  thinking: string
  isStreaming: boolean
  isThinkingActive?: boolean
}

export function ThinkingBlock({ thinking, isStreaming, isThinkingActive }: Props) {
  if (!thinking && !isStreaming && !isThinkingActive) return null

  const charCount = thinking.length

  return (
    <CollapsibleBlock
      label="Thinking"
      meta={thinking ? `${charCount} chars` : undefined}
      disabled={!thinking}
      right={isStreaming
        ? <span className="inline-block w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
        : undefined}
      bodyClassName="px-3 pb-2 max-h-[300px] overflow-y-auto scroll-thin"
    >
      <pre className="text-xs text-muted-foreground font-mono whitespace-pre-wrap leading-relaxed">
        {thinking}
      </pre>
    </CollapsibleBlock>
  )
}
