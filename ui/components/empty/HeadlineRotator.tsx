'use client'
import React, { useState, useEffect } from 'react'

interface Props { headlines: string[]; intervalMs: number }

export function HeadlineRotator({ headlines, intervalMs }: Props) {
  const [idx, setIdx] = useState(0)
  const prefersReduced =
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false

  useEffect(() => {
    if (headlines.length <= 1) return
    const id = setInterval(() => {
      setIdx(i => (i + 1) % headlines.length)
    }, intervalMs)
    return () => clearInterval(id)
  }, [headlines.length, intervalMs])

  return (
    <h1 className={`text-2xl font-semibold text-center text-foreground
                    ${prefersReduced ? '' : 'transition-opacity duration-400'}`}>
      {headlines[idx]}
    </h1>
  )
}
