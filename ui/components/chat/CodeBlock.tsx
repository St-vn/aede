'use client'
import React, { useState, useEffect } from 'react'
import { Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props { language?: string; code: string }

export function CodeBlock({ language, code }: Props) {
  const [highlighted, setHighlighted] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { createHighlighter } = await import('shiki')
        const hl = await createHighlighter({
          themes: ['github-dark'],
          langs: language ? [language as import('shiki').BuiltinLanguage] : [],
        })
        if (!cancelled) {
          setHighlighted(hl.codeToHtml(code, { lang: language ?? 'text', theme: 'github-dark' }))
        }
      } catch {
        // Shiki failed (unknown lang or WASM issue) — stay with raw display
      }
    })()
    return () => { cancelled = true }
  }, [code, language])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="relative rounded-lg overflow-hidden my-2 bg-card border border-border font-mono text-sm">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <span className="text-xs text-muted-foreground">{language || 'text'}</span>
        <Button variant="ghost" size="icon" className="h-6 w-6"
          aria-label="Copy code" onClick={handleCopy}>
          {copied ? <Check className="w-3 h-3 text-[--color-success]" /> : <Copy className="w-3 h-3" />}
        </Button>
      </div>
      {/* Fixed-height container prevents layout shift when Shiki swaps in */}
      {highlighted
        ? <div className="p-4 overflow-x-auto [&_pre]:m-0 [&_pre]:bg-transparent"
               dangerouslySetInnerHTML={{ __html: highlighted }} />
        : <pre className="p-4 overflow-x-auto whitespace-pre-wrap text-foreground">{code}</pre>
      }
    </div>
  )
}
