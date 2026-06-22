'use client'
import React from 'react'
import { Plug } from 'lucide-react'

interface Props {
  serverName: string
  toolName?: string
}

export function McpBadge({ serverName, toolName }: Props) {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono
      bg-primary/10 text-primary/80 border border-primary/20"
      title={`MCP server: ${serverName}${toolName ? ` · tool: ${toolName}` : ''}`}
    >
      <Plug className="w-2.5 h-2.5" />
      {serverName}
    </span>
  )
}
