import React from 'react'
import { FileText, X } from 'lucide-react'

interface Props {
  files: string[]
  onRemove: (filename: string) => void
}

export function FileChipBar({ files, onRemove }: Props) {
  if (files.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5 pb-2">
      {files.map(f => (
        <div key={f}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/10
                     text-xs text-primary border border-primary/20"
        >
          <FileText className="w-3 h-3 shrink-0" />
          <span className="max-w-[120px] truncate">{f}</span>
          <button
            type="button"
            onClick={() => onRemove(f)}
            className="hover:bg-primary/20 rounded-sm p-0.5 transition-colors"
            aria-label={`Remove ${f}`}
          >
            <X className="w-2.5 h-2.5" />
          </button>
        </div>
      ))}
    </div>
  )
}
