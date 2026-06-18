'use client'
import React, { useState } from 'react'
import { TriangleAlert, Check, X, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

interface GateItem {
  gateId: string
  toolName: string
  args: Record<string, unknown>
  mode?: string
  reason?: string
  options?: { id: string; label: string; key: string }[]
  decision?: 'allow_once' | 'allow_session' | 'deny'
}

interface Props {
  gates: GateItem[]
  onDecision: (gateId: string, decision: string, message?: string) => void
}

export function GateBatchCard({ gates, onDecision }: Props) {
  const [toolStates, setToolStates] = useState<Record<string, 'pending' | 'approved' | 'denied'>>({})
  const pendingCount = gates.filter(g => toolStates[g.gateId] === 'pending' || !toolStates[g.gateId]).length

  const decideOne = (gateId: string, decision: 'allow_once' | 'deny') => {
    setToolStates(s => ({ ...s, [gateId]: decision === 'allow_once' ? 'approved' : 'denied' }))
    onDecision(gateId, decision)
  }

  const approveAll = () => {
    gates.forEach(g => {
      setToolStates(s => ({ ...s, [g.gateId]: 'approved' }))
      onDecision(g.gateId, 'allow_once')
    })
  }

  const denyAll = () => {
    gates.forEach(g => {
      setToolStates(s => ({ ...s, [g.gateId]: 'denied' }))
      onDecision(g.gateId, 'deny')
    })
  }

  if (gates.length === 0) return null

  return (
    <div role="alert"
      className="border border-border border-l-2 border-l-[--color-warning] rounded-lg p-4 my-2 bg-card">
      <div className="flex items-center gap-2 mb-3">
        <TriangleAlert className="w-4 h-4 text-[--color-warning] shrink-0" />
        {gates[0]?.mode && (
          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted">
            {gates[0].mode}
          </span>
        )}
        <span className="text-sm font-medium text-foreground">
          {pendingCount} tool{pendingCount !== 1 ? 's' : ''} need{pendingCount === 1 ? 's' : ''} approval
        </span>
        <span className="ml-auto flex gap-1">
          <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={approveAll}
            disabled={pendingCount === 0} aria-label="Approve all">
            <Check className="w-3 h-3" /> All
          </Button>
          <Button size="sm" variant="outline" className="h-7 text-xs gap-1 text-destructive border-destructive hover:bg-destructive/10"
            onClick={denyAll} disabled={pendingCount === 0} aria-label="Deny all">
            <X className="w-3 h-3" /> All
          </Button>
        </span>
      </div>
      <ScrollArea className="max-h-64">
        <div className="space-y-2">
          {gates.map(g => {
            const state = toolStates[g.gateId] || 'pending'
            const cmdArg = (g.args.command as string) || JSON.stringify(g.args)
            return (
              <Collapsible key={g.gateId}>
                <div className="flex items-center gap-2 py-1.5 px-2 rounded-md hover:bg-muted/40">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    state === 'approved' ? 'bg-green-500' : state === 'denied' ? 'bg-red-500' : 'bg-yellow-500'
                  }`} />
                  <span className="font-mono text-xs flex-1 truncate">{g.toolName}</span>
                  <span className="text-[10px] text-muted-foreground truncate max-w-[160px]">{cmdArg}</span>
                  {state === 'pending' ? (
                    <span className="flex gap-0.5 ml-2">
                      <button className="p-0.5 rounded hover:bg-green-100 dark:hover:bg-green-900/30"
                        onClick={() => decideOne(g.gateId, 'allow_once')} title="Allow">
                        <Check className="w-3 h-3 text-green-600" />
                      </button>
                      <button className="p-0.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30"
                        onClick={() => decideOne(g.gateId, 'deny')} title="Deny">
                        <X className="w-3 h-3 text-red-600" />
                      </button>
                    </span>
                  ) : (
                    <span className={`text-[10px] ${state === 'approved' ? 'text-green-600' : 'text-red-600'}`}>
                      {state === 'approved' ? 'Approved' : 'Denied'}
                    </span>
                  )}
                </div>
              </Collapsible>
            )
          })}
        </div>
      </ScrollArea>
    </div>
  )
}
