'use client'
import React, { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

interface Props {
  messageId: string
  tokenCount?: number
}

export function ContextToggle({ messageId, tokenCount }: Props) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="inline-flex items-center gap-1">
      <Tooltip>
        <TooltipTrigger render={
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-0.5 rounded hover:bg-muted transition-colors text-muted-foreground/50 hover:text-muted-foreground"
            aria-label={isOpen ? 'Hide context info' : 'Show context info'}
          >
            {isOpen ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
          </button>
        } />
        <TooltipContent side="top">{isOpen ? 'Hide context info' : 'Show context info'}</TooltipContent>
      </Tooltip>
      {isOpen && tokenCount !== undefined && (
        <span className="text-xs text-muted-foreground/60 font-mono">
          {tokenCount} tokens
        </span>
      )}
    </div>
  )
}
