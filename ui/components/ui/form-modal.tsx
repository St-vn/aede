'use client'
import React, { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { ExternalLink } from 'lucide-react'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  children: React.ReactNode
  filePath?: string
  onOpenFile?: () => void
}

export function FormModal({ open, onOpenChange, title, children, filePath, onOpenFile }: Props) {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) contentRef.current?.focus()
  }, [open])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { e.stopPropagation(); onOpenChange(false); return }
    if (e.key === 'Tab') {
      const content = contentRef.current
      if (!content) return
      const focusable = content.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus()
      }
    }
  }

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center" onClick={() => onOpenChange(false)}>
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
      <div
        ref={contentRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={e => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        className="relative z-10 w-full max-w-lg rounded-xl border bg-popover text-popover-foreground shadow-lg max-h-[85vh] overflow-y-auto scroll-thin p-0 outline-none"
      >
        <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-border/60">
          <h2 className="text-sm font-semibold">{title}</h2>
          {filePath && onOpenFile && (
            <button
              onClick={onOpenFile}
              className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              title="Open in editor"
            >
              <ExternalLink className="w-3 h-3" />
              Edit file
            </button>
          )}
        </div>
        <div className="px-5 py-4">
          {children}
        </div>
      </div>
    </div>,
    document.body
  )
}
