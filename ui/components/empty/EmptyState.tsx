import React from 'react'
import { EMPTY_STATE } from '@/config/emptyState'
import { HeadlineRotator } from './HeadlineRotator'

export function EmptyState() {
  const cfg = EMPTY_STATE
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
      {cfg.image && <img src={cfg.image} alt="" className="max-h-32 opacity-80" />}
      <HeadlineRotator headlines={cfg.headlines} intervalMs={cfg.headlineIntervalMs} />
      {cfg.subtitleVisible && (
        <p className="text-sm text-muted-foreground">{cfg.subtitle}</p>
      )}
    </div>
  )
}
