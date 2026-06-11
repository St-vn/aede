'use client'
import React from 'react'
import { Loader2, CheckCircle2, XCircle, Ban, ChevronRight } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

type Status = 'running' | 'success' | 'error' | 'denied'
interface Props {
  toolName: string; status: Status; args: Record<string, unknown>
  output?: string; durationMs?: number; streamingOutput?: string
}

const STATUS_CONFIG: Record<Status, { icon: React.ReactNode; label: string; color: string }> = {
  running: { icon: <Loader2 className="w-3 h-3 animate-spin" />, label: 'running...', color: 'text-muted-foreground' },
  success: { icon: <CheckCircle2 className="w-3 h-3 text-[--color-success]" />, label: '', color: 'text-muted-foreground' },
  error:   { icon: <XCircle className="w-3 h-3 text-[--color-error]" />,   label: 'error',  color: 'text-[--color-error]' },
  denied:  { icon: <Ban className="w-3 h-3" />,                             label: 'denied', color: 'text-muted-foreground' },
}

export function ToolCallCard({ toolName, status, args, output, durationMs, streamingOutput }: Props) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.running
  const canExpand = status === 'success' || status === 'error'

  if (!canExpand) {
    return (
      <div className={`flex items-center gap-2 py-0.5 text-sm ${cfg.color}`}>
        <ChevronRight className="w-3 h-3 shrink-0" />
        <span className="font-mono">{toolName}</span>
        {cfg.icon}
        {cfg.label && <span>{cfg.label}</span>}
        {status === 'running' && streamingOutput && (
          <span className="text-xs text-muted-foreground/60 truncate max-w-[200px] ml-2">
            {streamingOutput.split('\n').pop()}
          </span>
        )}
      </div>
    )
  }

  return (
    <Collapsible>
      <CollapsibleTrigger className={`flex items-center gap-2 py-0.5 text-sm w-full text-left
                                      hover:text-foreground transition-colors ${cfg.color}`}>
        <ChevronRight className="w-3 h-3 shrink-0 transition-transform [&[data-state=open]]:rotate-90" />
        <span className="font-mono">{toolName}</span>
        {cfg.icon}
        {cfg.label && <span className={cfg.color}>{cfg.label}</span>}
        {durationMs !== undefined && <span>({durationMs}ms)</span>}
      </CollapsibleTrigger>
      <CollapsibleContent className="ml-5 mt-1 space-y-1">
        <pre className="text-xs bg-muted rounded p-2 overflow-x-auto font-mono">
          {JSON.stringify(args, null, 2)}
        </pre>
        {streamingOutput && (
          <pre className="text-xs bg-muted/50 rounded p-2 overflow-x-auto font-mono text-muted-foreground">
            {streamingOutput}
          </pre>
        )}
        {output && <pre className="text-xs bg-muted rounded p-2 overflow-x-auto font-mono">{output}</pre>}
      </CollapsibleContent>
    </Collapsible>
  )
}
