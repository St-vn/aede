import React from 'react'
import { format } from 'date-fns'

interface Props { content: string; timestamp: string }

export function UserMessage({ content, timestamp }: Props) {
  return (
    <div className="group flex justify-end gap-3 px-4 py-2">
      <div className="flex flex-col items-end gap-1 max-w-[80%]">
        <div className="bg-muted rounded-xl px-4 py-3 text-sm">{content}</div>
        <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          {format(new Date(timestamp), 'HH:mm')}
        </span>
      </div>
      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center
                      text-xs font-medium text-primary-foreground shrink-0 mt-1">
        S
      </div>
    </div>
  )
}
