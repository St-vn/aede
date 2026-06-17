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
  // A single trailing newline difference (old ends with \n, new doesn't or vice
  // versa) otherwise shows up as a phantom blank +/- row. Normalise it away so
  // the diff reflects real content changes.
  const lines = computeLineDiff(oldStr.replace(/\n$/, ''), newStr.replace(/\n$/, ''))
  const fileName = filePath.split(/[\\/]/).pop() || filePath
  let added = 0, removed = 0
  for (const dl of lines) {
    if (dl.type === 'add') added++
    else if (dl.type === 'remove') removed++
  }

  // Separate old/new line counters, both anchored at the real file start line
  // (1-based; falls back to 1 when the position is unknown).
  const base = startLine && startLine > 0 ? startLine : 1
  let oldNo = base, newNo = base
  // Width of the gutter scales with the largest line number shown.
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
        {lines.map((dl, idx) => {
          const isAdd = dl.type === 'add', isRem = dl.type === 'remove'
          // A single line-number column: new-side number for added/context,
          // old-side number for removed lines (GitHub-style unified diff).
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
              <span className={`whitespace-pre pr-3 ${text}`}>{dl.line}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function ToolCallCard({ toolName, status, args, output, durationMs, streamingOutput }: Props) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.running
  const canExpand = status === 'success' || status === 'error'
  // Any tool that supplies an old/new string pair renders as a diff,
  // regardless of name (ACP "Edit", a future native edit tool, etc.).
  const isEdit = typeof args.old_string === 'string'
    && typeof args.new_string === 'string'
  const startLine = typeof args._start_line === 'number' ? args._start_line : undefined

  // Running / denied: nothing to expand yet — show a flat row, but keep the
  // same bordered container so it lines up with the other blocks.
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
      bodyClassName="px-3 pb-2 space-y-1"
    >
      {isEdit ? (
        <DiffView
          filePath={String(args.file_path ?? args.path ?? '')}
          oldStr={args.old_string as string}
          newStr={args.new_string as string}
          startLine={startLine}
        />
      ) : (
        <pre className="text-xs bg-muted rounded p-2 overflow-x-auto font-mono">
          {JSON.stringify(args, null, 2)}
        </pre>
      )}
      {streamingOutput && (
        <pre className="text-xs bg-muted/50 rounded p-2 overflow-x-auto font-mono text-muted-foreground">
          {streamingOutput}
        </pre>
      )}
      {output && !isEdit && <pre className="text-xs bg-muted rounded p-2 overflow-x-auto font-mono">{output}</pre>}
    </CollapsibleBlock>
  )
}
