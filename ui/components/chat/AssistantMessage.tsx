'use client'
import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { Copy, Check, LoaderCircle } from 'lucide-react'
import { CodeBlock } from './CodeBlock'
import { ThinkingBlock } from './ThinkingBlock'
import { Dialog, DialogContent } from '@/components/ui/dialog'

/** Cycling status verbs shown next to the spinner while the assistant streams.
 *  Edit this array to customise the messages (e.g. add domain-specific terms). */
const STREAMING_VERBS = [
  'Thinking...', 'Reasoning...', 'Processing...', 'Analysing...',
  'Stir frying...', 'Drafting...', 'Cooking...', 'Deep frying...',
  'Ideating...', 'Building...', 'Architecting...', 'Designing...',
  'Orchestrating...', 'Assembling...', 'Mending...', 'Creating...',
]

/** Format a duration in milliseconds to a human-readable string.
 *  Examples: "0.3s", "2.7s", "45s", "1m 23s", "12m 7s", "1h 5m", "2d 14h" */
function formatDuration(ms: number): string {
  if (ms < 0) return '0s'

  const totalSeconds = Math.round(ms / 1000)
  if (totalSeconds === 0) return (ms / 1000).toFixed(1) + 's'

  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  const parts: string[] = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0) parts.push(`${minutes}m`)
  if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`)

  return parts.join(' ')
}

interface ThinkingSegment { text: string; seq: number }
interface Props {
  content: string
  isStreaming: boolean
  thinking?: string
  isThinkingActive?: boolean
  thinkingSegments?: ThinkingSegment[]
  /** Total wall-clock milliseconds the current agent turn has taken so far. */
  turnDurationMs?: number
}

export function AssistantMessage({ content, isStreaming, thinking, isThinkingActive, thinkingSegments, turnDurationMs }: Props) {
  const [verbIdx, setVerbIdx] = useState(0)

  // Cycle through streaming verbs while streaming.
  useEffect(() => {
    if (!isStreaming) return
    setVerbIdx(0)
    const id = setInterval(() => setVerbIdx(i => (i + 1) % STREAMING_VERBS.length), 2500)
    return () => clearInterval(id)
  }, [isStreaming])

  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  const lines = content.split('\n')
  const shouldCollapse = !isStreaming && (lines.length > 8 || content.length > 800)

  async function handleCopy() {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const segments = thinkingSegments && thinkingSegments.length > 0
    ? [...thinkingSegments].sort((a, b) => a.seq - b.seq)
    : null
  return (
    <div className="group py-2 text-sm" aria-live={isStreaming ? 'polite' : undefined}>
      {segments
        ? segments.map(s => <ThinkingBlock key={s.seq} thinking={s.text} isStreaming={false} />)
        : (thinking || isThinkingActive) && <ThinkingBlock thinking={thinking ?? ''} isStreaming={isStreaming} isThinkingActive={isThinkingActive} />}
      {shouldCollapse && !expanded ? (
        <div className="relative prose prose-invert prose-sm max-w-none">
          <p className="text-sm whitespace-pre-wrap break-words line-clamp-6">{content}</p>
          <div className="absolute bottom-0 right-0 pl-4 bg-gradient-to-l from-background via-background to-transparent text-muted-foreground">…</div>
        </div>
      ) : (
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={{
              pre({ children }) {
                const child = (Array.isArray(children) ? children[0] : children) as React.ReactElement<{ className?: string; children?: React.ReactNode }>
                const codeProps = child?.props ?? {}
                const className: string = codeProps.className || ''
                const match = /language-(\w+)/.exec(className)
                const code = String(codeProps.children ?? '').replace(/\n$/, '')
                return <CodeBlock language={match?.[1]} code={code} />
              },
              code({ children, ...props }) {
                return (
                  <code className="bg-muted rounded px-1 py-0.5 font-mono text-xs" {...props}>
                    {children}
                  </code>
                )
              },
              img({ src, alt, ...props }) {
                if (!src) return null
                return <img src={src} alt={alt ?? ''} {...props} />
              }
            }}
          >
            {content}
          </ReactMarkdown>
          {isStreaming && (
            <span aria-hidden="true" className="inline-flex items-center gap-1.5 text-muted-foreground/70 ml-1 align-middle">
              <LoaderCircle className="w-3.5 h-3.5 animate-spin" />
              <span className="text-xs">{STREAMING_VERBS[verbIdx]}</span>
            </span>
          )}
        </div>
      )}
      {shouldCollapse && (
        <div className="flex items-center gap-2 mt-2">
          <button
            className="text-xs text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 rounded"
            onClick={() => setExpanded(!expanded)}
            aria-label={expanded ? 'Show less' : 'Show more'}
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
          {!expanded && (
            <button
              className="text-xs text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 rounded"
              onClick={() => setModalOpen(true)}
              aria-label="open in modal"
            >
              Open in modal
            </button>
          )}
        </div>
      )}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity mt-2">
        <button
          aria-label="Copy assistant message"
          onClick={handleCopy}
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
        </button>
        {!isStreaming && turnDurationMs !== undefined && turnDurationMs > 0 && (
          <span className="text-sm text-muted-foreground/60 tabular-nums font-medium">
            {formatDuration(turnDurationMs)}
          </span>
        )}
      </div>
      <div aria-live="polite" className="sr-only">
        {copied && 'Copied to clipboard'}
      </div>
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh]">
          <pre className="text-sm whitespace-pre-wrap break-words overflow-y-auto max-h-[60vh]">{content}</pre>
        </DialogContent>
      </Dialog>
    </div>
  )
}
