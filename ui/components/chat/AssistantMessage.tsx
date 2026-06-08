'use client'
import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CodeBlock } from './CodeBlock'

interface Props { content: string; isStreaming: boolean }

export function AssistantMessage({ content, isStreaming }: Props) {
  return (
    <div className="group px-4 py-2 text-sm" aria-live={isStreaming ? 'polite' : undefined}>
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
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
