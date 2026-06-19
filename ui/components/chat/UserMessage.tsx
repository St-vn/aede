'use client'
import React, { useState } from 'react'
import { format } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { Copy, Check, Undo2 } from 'lucide-react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu'

interface Props {
  content: string
  timestamp: string
  messageId?: string
  onRewind?: (
    messageId: string,
    opts: { mode: 'truncate' | 'fork'; revertCode: boolean }
  ) => void
}

export function UserMessage({ content, timestamp, messageId, onRewind }: Props) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  const lines = content.split('\n')
  const shouldCollapse = lines.length > 8 || content.length > 800
  const displayContent = shouldCollapse && !expanded ? content.slice(0, 800) + '…' : content

  async function handleCopy() {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="group flex justify-end gap-3 py-2">
      <div className="flex flex-col items-end gap-1 max-w-[80%]">
        <div className="bg-muted rounded-xl px-4 py-3 text-sm">
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                code({ className, children, ...props }) {
                  return (
                    <code className="bg-background/50 rounded px-1 py-0.5 font-mono text-xs" {...props}>
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
              {displayContent}
            </ReactMarkdown>
          </div>
        </div>
        {shouldCollapse && (
          <div className="flex items-center gap-2">
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
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            aria-label="copy message"
            onClick={handleCopy}
            className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
          >
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          </button>
          {messageId && onRewind && (
            <DropdownMenu>
              <DropdownMenuTrigger aria-label="rewind" className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 rounded">
                <div className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                  <Undo2 className="size-3.5" />
                </div>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onRewind(messageId, { mode: 'truncate', revertCode: false })}>
                  Rewind in place
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onRewind(messageId, { mode: 'truncate', revertCode: true })}>
                  Rewind in place + revert code
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onRewind(messageId, { mode: 'fork', revertCode: false })}>
                  Fork to new branch
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <span className="text-xs text-muted-foreground">
            {format(new Date(timestamp), 'HH:mm')}
          </span>
        </div>
        <div aria-live="polite" className="sr-only">
          {copied && 'Copied to clipboard'}
        </div>
      </div>
      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center
                      text-xs font-medium text-primary-foreground shrink-0 mt-1">
        S
      </div>
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh]">
          <pre className="text-sm whitespace-pre-wrap break-words overflow-y-auto max-h-[60vh]">{content}</pre>
        </DialogContent>
      </Dialog>
    </div>
  )
}
