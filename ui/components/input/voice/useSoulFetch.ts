'use client'
import { useEffect, useState } from 'react'
import type { SoulData } from './matchWakeWord'

export function useSoulFetch(): { soul: SoulData | null; loading: boolean } {
  const [soul, setSoul] = useState<SoulData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/soul')
      .then(r => r.json())
      .then(data => {
        setSoul({
          name: data.name ?? null,
          wake_word: data.wake_word ?? null,
          aliases: data.aliases ?? [],
        })
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  return { soul, loading }
}
