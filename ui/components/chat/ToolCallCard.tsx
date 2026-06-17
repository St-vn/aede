'use client'
import React from 'react'
import { Loader2, CheckCircle2, XCircle, Ban } from 'lucide-react'
import { CollapsibleBlock } from './CollapsibleBlock'

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

type DiffLine = { type: 'add' | 'remove' | 'equal'; line: string }

function computeLineDiff(oldStr: string, newStr: string): DiffLine[] {
  const a = oldStr.split('\n')
  const b = newStr.split('\n')
  const m = a.length, n = b.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1] + 1 : Math.max(dp[i-1][j], dp[i][j-1])

  const result: DiffLine[] = []
  let i = m, j = n
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i-1] === b[j-1]) {
      result.unshift({ type: 'equal', line: a[i-1] })
      i--; j--
    } else if (j > 0 && (i === 0 || dp[i][j-1] >= dp[i-1][j])) {
      result.unshift({ type: 'add', line: b[j-1] })
      j--
    } else {
      result.unshift({ type: 'remove', line: a[i-1] })
      i--
    }
  }
  return result
}

function DiffView({ filePath, oldStr, newStr, startLine }: { filePath: string; oldStr: string; newStr: string; startLine?: number }) {
  const lines = computeLineDiff(oldStr.replace(/\n$/, ''), newStr.replace(/\n$/, ''))
  const fileName = filePath.split(/[\\/]/).pop() || filePath
  let added = 0, removed = 0
  for (const dl of lines) {
    if (dl.type === 'add') added++
    else if (dl.type === 'remove') removed++
  }

  const base = startLine && startLine > 0 ? startLine : 1
  let oldNo = base, newNo = base
  const maxNo = base + lines.length
  const gutterCh = String(maxNo).length

  return (
    <div className="text-xs rounded-md overflow-hidden font-mono border border-border">
      {filePath && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/60 border-b border-border">
          <span className="truncate text-foreground/80" title={filePath}>{fileName}</span>
          <span className="ml-auto flex items-center gap-2 shrink-0 tabular-nums">
            {added > 0 && <span className="text-green-400">+{added}</span>}
            {removed > 0 && <span className="text-red-400">-{removed}</span>}
          </span>
        </div>
      )}
      <div className="overflow-x-auto bg-background/40 py-1">
        <div className="min-w-full w-max">
        {lines.map((dl, idx) => {
          const isAdd = dl.type === 'add', isRem = dl.type === 'remove'
          let lineNo: number
          if (isAdd) { lineNo = newNo; newNo++ }
          else if (isRem) { lineNo = oldNo; oldNo++ }
          else { lineNo = newNo; oldNo++; newNo++ }
          const rowBg = isAdd ? 'bg-green-500/10' : isRem ? 'bg-red-500/10' : ''
          const gutter = isAdd ? 'text-green-500/60' : isRem ? 'text-red-500/60' : 'text-muted-foreground/40'
          const text = isAdd ? 'text-green-300' : isRem ? 'text-red-300' : 'text-muted-foreground'
          const sign = isAdd ? '+' : isRem ? '-' : ' '
          return (
            <div key={idx} className={`flex ${rowBg}`}>
              <span
                className={`select-none shrink-0 text-right px-2 ${gutter} tabular-nums`}
                style={{ minWidth: `${gutterCh + 1}ch` }}
              >
                {lineNo}
              </span>
              <span className={`select-none shrink-0 w-4 text-center ${text}`}>{sign}</span>
              <span className={`whitespace-pre pr-3 flex-1 ${text}`}>{dl.line}</span>
            </div>
          )
        })}
      </div>
    </div>
    </div>
  )
}

const PRIMARY_KEYS = ['file_path', 'path', 'command', 'cmd', 'query', 'url', 'pattern', 'name', 'repo', 'branch', 'content', 'message', 'code']

function getPrimaryValue(args: Record<string, unknown>): string | undefined {
  for (const key of PRIMARY_KEYS) {
    const v = args[key]
    if (typeof v === 'string' && v.length > 0) return v
  }
  const first = Object.values(args)[0]
  return typeof first === 'string' ? first : undefined
}

function ArgsView({ args, exclude }: { args: Record<string, unknown>; exclude?: string }) {
  const entries = Object.entries(args).filter(([k]) => k !== exclude && PRIMARY_KEYS.indexOf(k) === -1 || k === exclude)
    .filter(([k]) => k !== exclude)
  if (entries.length === 0) return null
  return (
    <div className="text-xs font-mono space-y-0.5">
      {entries.map(([k, v]) => {
        let display: string
        if (typeof v === 'string') display = v
        else if (v === null || v === undefined) display = String(v)
        else if (typeof v === 'object') display = JSON.stringify(v)
        else display = String(v)
        if (display.length > 300) display = display.slice(0, 300) + '...'
        return (
          <div key={k} className="flex gap-2 py-0.5">
            <span className="text-muted-foreground shrink-0">{k}:</span>
            <span className="text-foreground/80 break-all whitespace-pre-wrap">{display}</span>
          </div>
        )
      })}
    </div>
  )
}

export function ToolCallCard({ toolName, status, args, output, durationMs, streamingOutput }: Props) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.running
  const canExpand = status === 'success' || status === 'error'
  const isEdit = typeof args.old_string === 'string'
    && typeof args.new_string === 'string'
  const startLine = typeof args._start_line === 'number' ? args._start_line : undefined

  // Primary value for the header (file path, command, query, etc.)
  const primaryValue = !isEdit ? getPrimaryValue(args) : undefined
  const primaryName = primaryValue
    ? primaryValue.split(/[\\/]/).pop() || primaryValue
    : toolName

  if (!canExpand) {
    return (
      <CollapsibleBlock
        label={<span className="font-mono">{toolName}</span>}
        disabled
        right={
          <span className="flex items-center gap-1.5">
            {cfg.icon}
            {cfg.label && <span className={cfg.color}>{cfg.label}</span>}
            {status === 'running' && streamingOutput && (
              <span className="text-[10px] text-muted-foreground/60 truncate max-w-[200px]">
                {streamingOutput.split('\n').pop()}
              </span>
            )}
          </span>
        }
      >
        {null}
      </CollapsibleBlock>
    )
  }

  return (
    <CollapsibleBlock
      label={<span className="font-mono">{toolName}</span>}
      meta={durationMs !== undefined && durationMs > 0 ? `${durationMs}ms` : undefined}
      right={
        <span className="flex items-center gap-1.5">
          {cfg.icon}
          {cfg.label && <span className={cfg.color}>{cfg.label}</span>}
        </span>
      }
      bodyClassName="p-0"
    >
      {isEdit ? (
        <DiffView
          filePath={String(args.file_path ?? args.path ?? '')}
          oldStr={args.old_string as string}
          newStr={args.new_string as string}
          startLine={startLine}
        />
      ) : (
        <div className="text-xs rounded-md overflow-hidden font-mono border border-border">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/60 border-b border-border">
            <span className="truncate text-foreground/80" title={primaryValue}>{primaryName}</span>
            {primaryValue && primaryName !== primaryValue && (
              <span className="truncate text-muted-foreground/50 text-[10px]" title={primaryValue}>{primaryValue}</span>
            )}
          </div>
          <div className="overflow-x-auto bg-background/40 py-2 px-3">
            <ArgsView args={args} />
          </div>
        </div>
      )}
      {streamingOutput && (
        <pre className="text-xs rounded mx-2 mb-2 p-2 overflow-y-auto overflow-x-hidden max-h-[300px] scroll-thin whitespace-pre-wrap break-words font-mono text-muted-foreground">
          {streamingOutput}
        </pre>
      )}
      {output && !isEdit && <pre className="text-xs rounded mx-2 mb-2 p-2 overflow-y-auto overflow-x-hidden max-h-[300px] scroll-thin whitespace-pre-wrap break-words font-mono">{output}</pre>}
    </CollapsibleBlock>
  )
}
