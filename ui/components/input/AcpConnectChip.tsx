'use client'
import React from 'react'
import { Wifi, WifiOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useStatus, useConnect, useDisconnect } from '@/hooks/useAcpAgents'

const ACP_AGENTS = ['codex', 'claude-code', 'gemini', 'agy', 'cline', 'cursor', 'goose']

interface Props { model: string }

export function AcpConnectChip({ model }: Props) {
  const { data: status } = useStatus()
  const connectMut = useConnect()
  const disconnectMut = useDisconnect()
  const autoTriggered = React.useRef(false)

  const agent = model.split('/')[0]
  const isConnected = status?.sessions?.includes(agent) ?? false

  React.useEffect(() => {
    if (!ACP_AGENTS.includes(agent)) return
    if (isConnected || connectMut.isPending || autoTriggered.current) return
    autoTriggered.current = true
    connectMut.mutate(agent)
  }, [agent, isConnected, connectMut])

  if (!ACP_AGENTS.includes(agent)) return null

  if (isConnected) {
    return (
      <div className="flex items-center gap-1">
        <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground font-medium">
          <Wifi className="w-2.5 h-2.5 text-green-500" />
          Connected
        </span>
        <Button variant="ghost" size="icon-sm" className="h-6 w-6 text-muted-foreground hover:text-destructive"
          onClick={() => disconnectMut.mutate(agent)}>
          <WifiOff className="w-3 h-3" />
        </Button>
      </div>
    )
  }

  if (connectMut.isPending) {
    return (
      <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground font-medium">
        <Loader2 className="w-2.5 h-2.5 animate-spin" />
        Connecting
      </span>
    )
  }

  if (connectMut.isError) {
    const msg = connectMut.error instanceof Error ? connectMut.error.message : 'Connection failed'
    return (
      <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-destructive/10 text-destructive font-medium cursor-pointer"
        title={msg} onClick={() => { autoTriggered.current = false; connectMut.mutate(agent) }}>
        <WifiOff className="w-2.5 h-2.5" />
        Failed
      </span>
    )
  }

  return null
}
