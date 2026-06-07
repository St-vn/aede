'use client'
import React, { useState } from 'react'
import { TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

type GateScope = 'allow_once' | 'allow_session' | 'allow_project' | 'allow_global' | 'deny' | 'redirect'
interface GateDecisionEvent { gateId: string; decision: GateScope; message?: string }
interface Props {
  gateId: string; toolName: string; args: Record<string, unknown>
  onDecision: (ev: GateDecisionEvent) => void
}

export function GateCard({ gateId, toolName, args, onDecision }: Props) {
  const [redirectOpen, setRedirectOpen] = useState(false)
  const [redirectMsg, setRedirectMsg] = useState('')
  const decide = (decision: GateScope, message?: string) =>
    onDecision({ gateId, decision, message })

  const cmdArg = (args.command as string) || JSON.stringify(args)

  return (
    <div role="alert"
      className="border border-border border-l-2 border-l-[--color-warning] rounded-lg p-4 my-2 bg-card">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <TriangleAlert className="w-4 h-4 text-[--color-warning] shrink-0" />
        <span className="font-mono text-sm text-foreground">{toolName}</span>
        <span className="ml-auto text-xs font-medium text-[--color-warning] uppercase tracking-wide">
          Needs Approval
        </span>
      </div>
      {/* Args */}
      <pre className="font-mono text-sm bg-muted rounded px-3 py-2 mb-3 overflow-x-auto whitespace-pre-wrap">
        {cmdArg}
      </pre>
      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => decide('allow_once')} aria-label="Allow once">
          Allow once
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger render={
            <Button size="sm" variant="outline">Always ▼</Button>
          } />
          <DropdownMenuContent>
            {(['allow_session', 'allow_project', 'allow_global'] as const).map(scope => (
              <DropdownMenuItem key={scope} onClick={() => decide(scope)}>
                {scope.replace('allow_', '')}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button size="sm" variant="outline"
          className="text-destructive border-destructive hover:bg-destructive/10"
          onClick={() => decide('deny')} aria-label="Deny">
          Deny
        </Button>
        <Collapsible open={redirectOpen} onOpenChange={setRedirectOpen}>
          <CollapsibleTrigger render={
            <Button size="sm" variant="ghost" aria-label="Redirect">Redirect</Button>
          } />
          <CollapsibleContent className="mt-2 w-full flex gap-2">
            <Input
              aria-label="Tell the agent what to do instead"
              placeholder="Tell the agent what to do instead..."
              value={redirectMsg}
              onChange={e => setRedirectMsg(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && decide('redirect', redirectMsg)}
            />
            <Button size="sm" onClick={() => decide('redirect', redirectMsg)}>Send</Button>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  )
}
