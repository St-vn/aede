'use client'
import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'

export interface SoulData {
  name: string | null
  wake_word: string | null
  aliases: string[]
}

export function useSoulFetch(): { soul: SoulData | null; loading: boolean } {
  const [soul, setSoul] = useState<SoulData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<{ name?: string | null; wake_word?: string | null; aliases?: string[] }>('/api/soul')
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
