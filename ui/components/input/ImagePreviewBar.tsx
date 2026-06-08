'use client'
import React from 'react'
import { X, Image } from 'lucide-react'

export interface ImageAttachment {
  id: string
  dataUrl: string
  mime: string
  filename: string
}

interface Props {
  images: ImageAttachment[]
  onRemove: (id: string) => void
}

export function ImagePreviewBar({ images, onRemove }: Props) {
  if (images.length === 0) return null

  return (
    <div className="flex items-center gap-2 px-1 pb-2 overflow-x-auto" data-testid="image-preview-bar">
      {images.map(img => (
        <div
          key={img.id}
          className="relative group shrink-0"
        >
          <img
            src={img.dataUrl}
            alt={img.filename}
            className="w-16 h-16 rounded-md object-cover border border-border"
          />
          <button
            onClick={() => onRemove(img.id)}
            className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-background border border-border
                       flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity
                       hover:bg-destructive hover:text-destructive-foreground"
            aria-label={`Remove ${img.filename}`}
          >
            <X className="w-3 h-3" />
          </button>
          <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-[9px] text-white px-1 truncate rounded-b-md text-center">
            {img.filename}
          </div>
        </div>
      ))}
    </div>
  )
}
