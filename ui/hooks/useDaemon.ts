import useSWR from 'swr'
import { apiFetch } from '@/lib/api'

export interface DaemonStatus {
  running: boolean
  pid: number | null
  port: number | null
}

export function useDaemonStatus() {
  return useSWR<DaemonStatus>('/api/daemon/status', () =>
    apiFetch<DaemonStatus>('/api/daemon/status'),
  )
}
