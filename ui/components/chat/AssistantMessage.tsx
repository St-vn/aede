'use client'
import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { LoaderCircle } from 'lucide-react'
import { CodeBlock } from './CodeBlock'
import { ThinkingBlock } from './ThinkingBlock'

/** Cycling status verbs shown next to the spinner while the assistant streams.
 *  Edit this array to customise the messages (e.g. add domain-specific terms). */
const STREAMING_VERBS = [
  'Thinking...', 'Reasoning...', 'Processing...', 'Analysing...',
  'Stir frying...', 'Drafting...', 'Cooking...', 'Deep frying...',
  'Ideating...', 'Building...', 'Architecting...', 'Designing...',
  'Orchestrating...', 'Assembling...', 'Welding...', 'Creating...',
]

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

  const segments = thinkingSegments && thinkingSegments.length > 0
    ? [...thinkingSegments].sort((a, b) => a.seq - b.seq)
    : null
  return (
    <div className="group py-2 text-sm" aria-live={isStreaming ? 'polite' : undefined}>
      {segments
        ? segments.map(s => <ThinkingBlock key={s.seq} thinking={s.text} isStreaming={false} />)
        : (thinking || isThinkingActive) && <ThinkingBlock thinking={thinking ?? ''} isStreaming={isStreaming} isThinkingActive={isThinkingActive} />}
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{
            pre({ children }) {
              const child: any = Array.isArray(children) ? children[0] : children
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
      {!isStreaming && turnDurationMs !== undefined && turnDurationMs > 0 && (
        <div className="flex justify-end mt-1">
          <span className="text-[10px] text-muted-foreground/50 tabular-nums">
            {(turnDurationMs / 1000).toFixed(1)}s
          </span>
        </div>
      )}
    </div>
  )
}
