'use client'
import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { CodeBlock } from './CodeBlock'
import { ThinkingBlock } from './ThinkingBlock'

interface ThinkingSegment { text: string; seq: number }
interface Props {
  content: string
  isStreaming: boolean
  thinking?: string
  isThinkingActive?: boolean
  /** Ordered per-step thinking segments (ACP turns). When present these are
   *  rendered as separate blocks instead of the single `thinking` blob, so a
   *  multi-step turn shows one thinking block per reasoning step. */
  thinkingSegments?: ThinkingSegment[]
}

export function AssistantMessage({ content, isStreaming, thinking, isThinkingActive, thinkingSegments }: Props) {
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
            // Fenced/indented code blocks arrive as <pre><code>…</code></pre>.
            // Route the whole block through CodeBlock so EVERY block — with or
            // without a language tag — gets the same full-width collapsible
            // chrome (a bare ``` block has no language- class but is still a
            // block, not inline code).
            pre({ children }) {
              const child: any = Array.isArray(children) ? children[0] : children
              const codeProps = child?.props ?? {}
              const className: string = codeProps.className || ''
              const match = /language-(\w+)/.exec(className)
              const code = String(codeProps.children ?? '').replace(/\n$/, '')
              return <CodeBlock language={match?.[1]} code={code} />
            },
            // `code` now only handles true inline code (block code is consumed
            // by the `pre` override above).
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
          <span aria-hidden="true" className="inline-block cursor-blink font-mono ml-0.5 align-middle">
            ▌
          </span>
        )}
      </div>
    </div>
  )
}
