'use client'
import React, { useState } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'

interface Props {
  sessionId: string | null
}

interface ContextUsage {
  used: number
  total: number
}

export function ContextBar({ sessionId }: Props) {
  const [usage, setUsage] = useState<ContextUsage | null>(null)
  const [showCompact, setShowCompact] = useState(false)

  useWebSocket(sessionId, (ev) => {
    if (ev.type === 'context_usage') {
      setUsage({ used: ev.used as number, total: ev.total as number })
    }
  })

  if (!usage || usage.total === 0) return null

  const pct = Math.min((usage.used / usage.total) * 100, 100)
  const barColor = pct < 60 ? 'bg-green-500' : pct < 80 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div
      className="max-w-[760px] mx-auto w-full px-4 pb-1 cursor-pointer select-none"
      onClick={() => setShowCompact(!showCompact)}
      title={`${usage.used.toLocaleString()} / ${usage.total.toLocaleString()} tokens (${pct.toFixed(0)}%)`}
    >
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[10px] font-mono text-muted-foreground/60 whitespace-nowrap">
          {pct.toFixed(0)}%
        </span>
        {showCompact && (
          <span className="text-[10px] font-mono text-muted-foreground/40">
            {usage.used.toLocaleString()}/{usage.total.toLocaleString()}
          </span>
        )}
      </div>
    </div>
  )
}
