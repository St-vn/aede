'use client'
import React from 'react'
import { Separator } from '@/components/ui/separator'
import { Card } from '@/components/ui/card'
import { useSessionTokens } from '@/hooks/useTokens'
import { BarChart3, DollarSign, Cpu } from 'lucide-react'

interface Props {
  sessionId?: string | null
}

export function ContextTab({ sessionId }: Props) {
  const { data: tokenData, isLoading } = useSessionTokens(sessionId || null)

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Context Usage</h3>
      <Separator />
      {!sessionId ? (
        <p className="text-xs text-muted-foreground">Select a session to view token usage.</p>
      ) : isLoading ? (
        <p className="text-xs text-muted-foreground">Loading...</p>
      ) : tokenData ? (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <Card className="p-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <Cpu className="w-3.5 h-3.5" /> Total Tokens
              </div>
              <p className="text-lg font-semibold">
                {(tokenData.totals.input_tokens + tokenData.totals.output_tokens).toLocaleString()}
              </p>
            </Card>
            <Card className="p-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <BarChart3 className="w-3.5 h-3.5" /> Cache Hit Rate
              </div>
              <p className="text-lg font-semibold">
                {tokenData.totals.input_tokens > 0
                  ? `${((tokenData.totals.cached_tokens / tokenData.totals.input_tokens) * 100).toFixed(0)}%`
                  : '\u2014'}
              </p>
            </Card>
            <Card className="p-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <DollarSign className="w-3.5 h-3.5" /> Est. Cost
              </div>
              <p className="text-lg font-semibold">
                {tokenData.estimated_cost_usd !== null
                  ? `$${tokenData.estimated_cost_usd.toFixed(4)}`
                  : '\u2014'}
              </p>
            </Card>
          </div>
          <Separator />
          <div className="space-y-1">
            <h4 className="text-xs font-medium text-muted-foreground">Per-Source Breakdown</h4>
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground/60">
                Live per-source breakdown is shown in the context bar above the chat input.
                This section will display aggregated source data from the session.
              </p>
            </div>
          </div>
          <Separator />
          <div className="space-y-1">
            <h4 className="text-xs font-medium text-muted-foreground">Per-Turn Breakdown</h4>
            {tokenData.turns.length === 0 ? (
              <p className="text-xs text-muted-foreground">No turn data yet.</p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {tokenData.turns.map((turn, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] font-mono px-2 py-1 rounded hover:bg-muted/50">
                    <span className="text-muted-foreground w-6">#{turn.turn_number}</span>
                    <span className="flex-1">
                      <span className="text-blue-500">Input:{turn.input_tokens}</span>
                      {' '}
                      <span className="text-green-500">Output:{turn.output_tokens}</span>
                      {turn.cached_tokens > 0 && <span className="text-yellow-500 ml-1">Cached:{turn.cached_tokens}</span>}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{turn.role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">Failed to load token data.</p>
      )}
    </div>
  )
}
