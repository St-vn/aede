'use client'
import React, { useState } from 'react'
import { Loader2, ExternalLink, ChevronDown, ChevronRight, User } from 'lucide-react'
import { Card } from '@/components/ui/card'

interface SubagentStatus {
  agentName: string
  task: string
  status: 'running' | 'completed' | 'error'
  sessionId?: string
  turnCount?: number
}

interface Props {
  status: SubagentStatus
}

export function SubagentToolCard({ status }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Card className="px-3 py-2 my-1 border border-border/60 bg-muted/30">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left"
      >
        {expanded ? <ChevronDown className="w-3 h-3 shrink-0 text-muted-foreground" /> : <ChevronRight className="w-3 h-3 shrink-0 text-muted-foreground" />}
        <User className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        <span className="text-xs font-medium truncate flex-1">{status.agentName}</span>
        {status.status === 'running' && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            Working...
          </span>
        )}
        {status.status === 'completed' && (
          <span className="text-[10px] text-green-600 dark:text-green-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Done{status.turnCount ? ` (${status.turnCount} turns)` : ''}
          </span>
        )}
        {status.status === 'error' && (
          <span className="text-[10px] text-red-500">Error</span>
        )}
      </button>
      {expanded && (
        <div className="mt-2 pt-2 border-t border-border/40 text-[11px] text-muted-foreground space-y-1">
          <p><span className="font-medium">Task:</span> {status.task}</p>
          {status.sessionId && (
            <p className="flex items-center gap-1">
              <span className="font-medium">Session:</span>
              <span className="font-mono text-[10px]">{status.sessionId.slice(0, 8)}...</span>
              <ExternalLink className="w-3 h-3 ml-1" />
            </p>
          )}
        </div>
      )}
    </Card>
  )
}
