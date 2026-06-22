'use client'
import React, { useState } from 'react'
import { BrainCircuit } from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

interface Props {
  sessionId: string | null
}

export function LearningsChip({ sessionId }: Props) {
  const [count, setCount] = useState<number | null>(null)

  useWebSocket(sessionId, (ev) => {
    if (ev.type === 'learnings_injected') {
      setCount(ev.count as number)
    }
  })

  if (count === null || count === 0) return null

  return (
    <Tooltip>
      <TooltipTrigger>
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono
          bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 cursor-default">
          <BrainCircuit className="w-2.5 h-2.5" />
          {count} learning{count > 1 ? 's' : ''}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top">Active learnings from memory store</TooltipContent>
    </Tooltip>
  )
}
