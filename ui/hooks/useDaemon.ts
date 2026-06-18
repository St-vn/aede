import useSWR from 'swr'
import { apiFetch } from '@/lib/api'

export interface DaemonStatus {
  running: boolean
  pid: number | null
  port: number | null
}

export function useDaemonStatus() {
  return useSWR<DaemonStatus>('/daemon/status', () =>
    apiFetch<DaemonStatus>('/daemon/status'),
  )
}
