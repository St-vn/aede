'use client'
import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { CodeBlock } from './CodeBlock'
import { ThinkingBlock } from './ThinkingBlock'

interface Props { content: string; isStreaming: boolean; thinking?: string }

export function AssistantMessage({ content, isStreaming, thinking }: Props) {
  return (
    <div className="group px-4 py-2 text-sm" aria-live={isStreaming ? 'polite' : undefined}>
      {thinking && <ThinkingBlock thinking={thinking} isStreaming={isStreaming} />}
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '')
              return match ? (
                <CodeBlock language={match[1]} code={String(children).replace(/\n$/, '')} />
              ) : (
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
