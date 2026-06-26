'use client'
import React, { useState } from 'react'
import { AlertTriangle, AlertCircle, Info, ChevronDown, ChevronRight } from 'lucide-react'
import { Card } from '@/components/ui/card'

interface CriticFinding {
  severity: 'error' | 'warning' | 'info'
  message: string
  file?: string
  line?: number
}

interface Props {
  findings: CriticFinding[]
}

function SeverityIcon({ severity }: { severity: string }) {
  switch (severity) {
    case 'error': return <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
    case 'warning': return <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 shrink-0" />
    default: return <Info className="w-3.5 h-3.5 text-blue-500 shrink-0" />
  }
}

export function CriticCard({ findings }: Props) {
  const [expanded, setExpanded] = useState(false)
  if (findings.length === 0) return null

  const errorCount = findings.filter(f => f.severity === 'error').length
  const warningCount = findings.filter(f => f.severity === 'warning').length

  return (
    <Card className="my-2 border border-border/60">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left px-3 py-2 text-xs"
      >
        {expanded ? <ChevronDown className="w-3 h-3 shrink-0 text-muted-foreground" /> : <ChevronRight className="w-3 h-3 shrink-0 text-muted-foreground" />}
        <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 shrink-0" />
        <span className="font-medium">Critic</span>
        {errorCount > 0 && <span className="text-red-500">{errorCount} error{errorCount > 1 ? 's' : ''}</span>}
        {warningCount > 0 && <span className="text-yellow-500 ml-1">{warningCount} warning{warningCount > 1 ? 's' : ''}</span>}
        <span className="text-muted-foreground ml-auto">{findings.length} finding{findings.length > 1 ? 's' : ''}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-2 space-y-1.5 border-t border-border/40 pt-1.5">
          {findings.map((f, i) => (
            <div key={i} className="flex items-start gap-2 text-[11px]">
              <SeverityIcon severity={f.severity} />
              <div className="flex-1 min-w-0">
                <p>{f.message}</p>
                {(f.file || f.line) && (
                  <p className="text-xs font-mono text-muted-foreground/60 mt-0.5">
                    {f.file}{f.line ? `:${f.line}` : ''}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
