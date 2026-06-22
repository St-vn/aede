'use client'
import React, { useState, useEffect, useRef } from 'react'
import { Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CollapsibleBlock } from './CollapsibleBlock'

interface Props { language?: string; code: string }

let highlighterPromise: Promise<import('shiki').Highlighter> | null = null
async function getHighlighter(language?: string) {
  if (!highlighterPromise) {
    highlighterPromise = (async () => {
      const { createHighlighter } = await import('shiki')
      return createHighlighter({
        themes: ['github-dark'],
        langs: language ? [language as import('shiki').BuiltinLanguage] : [],
      })
    })()
  }
  return highlighterPromise
}

export function CodeBlock({ language, code }: Props) {
  const [highlighted, setHighlighted] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const hlRef = useRef<import('shiki').Highlighter | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const hl = await getHighlighter(language)
        hlRef.current = hl
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
    <CollapsibleBlock
      label={language || 'text'}
      defaultOpen
      right={
        <Button variant="ghost" size="icon" className="h-6 w-6"
          aria-label="Copy code"
          // Don't toggle the block when copying.
          onClick={(e) => { e.stopPropagation(); handleCopy() }}>
          {copied ? <Check className="w-3 h-3 text-[--color-success]" /> : <Copy className="w-3 h-3" />}
        </Button>
      }
      bodyClassName="font-mono text-sm"
    >
      {/* Fixed-height container prevents layout shift when Shiki swaps in */}
      {highlighted
        ? <div className="p-4 overflow-x-auto [&_pre]:m-0 [&_pre]:bg-transparent"
               dangerouslySetInnerHTML={{ __html: highlighted }} />
        : <pre className="p-4 overflow-x-auto whitespace-pre-wrap text-foreground">{code}</pre>
      }
    </CollapsibleBlock>
  )
}
