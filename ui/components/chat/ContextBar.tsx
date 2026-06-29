'use client'
import React, { useState } from 'react'
import { toast } from 'sonner'
import { apiFetch } from '@/lib/api'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { TokenBucket } from '@/hooks/useTokens'

interface Props {
  sessionId: string | null
}

interface ContextUsage {
  used: number
  total: number
  buckets: TokenBucket[]
  compactions: string[]
}

const BUCKET_LABELS: Record<string, string> = {
  system: 'System',
  instructions: 'Instructions',
  skills: 'Skills',
  mcp: 'MCP',
  conversation: 'Conversation',
}

const BUCKET_COLORS: Record<string, string> = {
  system: 'bg-blue-500',
  instructions: 'bg-purple-500',
  skills: 'bg-cyan-500',
  mcp: 'bg-orange-500',
  conversation: 'bg-green-500',
}

export function ContextBar({ sessionId }: Props) {
  const [usage, setUsage] = useState<ContextUsage | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [compacting, setCompacting] = useState(false)

  useWebSocket(sessionId, (ev) => {
    if (ev.type === 'context_usage') {
      setUsage({
        used: ev.used as number,
        total: ev.total as number,
        buckets: (ev.buckets as TokenBucket[]) || [],
        compactions: (ev.compactions as string[]) || [],
      })
    }
  })

  if (!usage || usage.total === 0) return null

  const pct = Math.min((usage.used / usage.total) * 100, 100)
  const barColor = pct < 60 ? 'bg-green-500' : pct < 80 ? 'bg-yellow-500' : 'bg-red-500'

  const handleCompact = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setCompacting(true)
    try {
      await apiFetch('/api/compact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
    } catch {
      toast.error('Failed to compact context')
    }
    setCompacting(false)
  }

  return (
    <div className="max-w-[760px] mx-auto w-full px-4 pb-1">
      <div
        className="cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
        title={`${usage.used.toLocaleString()} / ${usage.total.toLocaleString()} tokens (${pct.toFixed(0)}%)`}
      >
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${barColor}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-xs font-mono text-muted-foreground/60 whitespace-nowrap">
            {pct.toFixed(0)}%
          </span>
        </div>
      </div>

      {expanded && (
        <div className="mt-2 p-2 rounded-lg border bg-card text-card-foreground text-xs space-y-2">
          {usage.buckets.length > 0 && (
            <div className="space-y-1">
              <p className="font-medium text-muted-foreground text-[10px] uppercase tracking-wider">
                Per-Source Breakdown
              </p>
              {usage.buckets.map((b) => {
                const bucketPct = usage.total > 0 ? ((b.tokens / usage.total) * 100).toFixed(1) : '0'
                const color = BUCKET_COLORS[b.source] || 'bg-gray-500'
                return (
                  <div key={b.source} className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${color}`} />
                    <span className="flex-1 text-muted-foreground">
                      {BUCKET_LABELS[b.source] || b.source}
                    </span>
                    <span className="font-mono text-muted-foreground/60">
                      {b.tokens.toLocaleString()} ({bucketPct}%)
                    </span>
                  </div>
                )
              })}
            </div>
          )}

          {usage.compactions.length > 0 && (
            <div className="text-xs text-muted-foreground/40">
              Last compaction: {usage.compactions[usage.compactions.length - 1]}
            </div>
          )}

          <button
            onClick={handleCompact}
            disabled={compacting}
            className="w-full text-[11px] py-1 rounded bg-muted hover:bg-muted/80 text-muted-foreground transition-colors disabled:opacity-50"
          >
            {compacting ? 'Compacting...' : 'Compact'}
          </button>
        </div>
      )}
    </div>
  )
}
