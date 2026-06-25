'use client'
import React, { useState } from 'react'
import { ChevronDown } from 'lucide-react'

interface Props {
  /** Left-aligned label (e.g. "Thinking", a tool name, a language). */
  label: React.ReactNode
  /** Optional small meta shown after the label (e.g. "120 chars", "14ms"). */
  meta?: React.ReactNode
  /** Optional content rendered on the right, before the chevron (status dot,
   *  spinner, copy button…). */
  right?: React.ReactNode
  /** Collapsible body. */
  children: React.ReactNode
  /** Start expanded. Defaults to collapsed (matches the thinking block). */
  defaultOpen?: boolean
  /** Disable toggling (e.g. nothing to show yet while streaming). */
  disabled?: boolean
  /** Extra classes for the scrollable body wrapper. */
  bodyClassName?: string
}

/**
 * Shared collapsible container so every block in the chat (thinking, tool
 * calls, code blocks) shares one toggle format: a bordered rounded box with a
 * header button and a right-aligned ChevronDown that rotates on open, plus a
 * grid-rows height animation.
 */
export function CollapsibleBlock({
  label, meta, right, children, defaultOpen = false, disabled = false, bodyClassName = '',
}: Props) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border border-border rounded-lg my-2 overflow-hidden">
      {/* The label+chevron is the toggle button; `right` lives outside it so
          it can hold its own interactive controls (e.g. a copy button) without
          nesting <button> elements. */}
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground">
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className="flex items-center gap-2 flex-1 min-w-0 text-left
                     hover:text-foreground transition-colors
                     disabled:cursor-default disabled:hover:text-muted-foreground"
        >
          <span className="font-medium truncate">{label}</span>
          {meta && <span className="text-xs text-muted-foreground/60 shrink-0">{meta}</span>}
        </button>
        <span className="flex items-center gap-2 shrink-0">
          {right}
          {!disabled && (
            <button
              type="button"
              onClick={() => setIsOpen(!isOpen)}
              aria-label={isOpen ? 'Collapse' : 'Expand'}
              className="hover:text-foreground transition-colors"
            >
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
          )}
        </span>
      </div>
      <div className={`grid transition-all duration-200 ease-out ${isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
        <div className="overflow-hidden min-h-0">
          <div className={bodyClassName}>
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}
