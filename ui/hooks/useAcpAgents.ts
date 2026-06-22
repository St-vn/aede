import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

interface AcpConfig {
  name: string
  command: string
  args: string[]
  credentials_ref: string | null
}

interface AcpConfigsResponse {
  configs: AcpConfig[]
}

interface AcpStatusResponse {
  connected: boolean
  active: string | null
  sessions: string[]
}

export const useConfigs = () =>
  useQuery({
    queryKey: ['acp', 'configs'],
    queryFn: () => apiFetch<AcpConfigsResponse>('/api/acp/configs'),
  })

export const useStatus = () =>
  useQuery({
    queryKey: ['acp', 'status'],
    queryFn: () => apiFetch<AcpStatusResponse>('/api/acp/status'),
    refetchInterval: 5000,
  })

export const useConnect = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ status: string; name: string; session_id: string }>('/api/acp/connect', {
        method: 'POST',
        body: JSON.stringify({ name }),
        headers: { 'Content-Type': 'application/json' },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['acp'] })
    },
  })
}

export const useDisconnect = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ status: string; name: string }>('/api/acp/disconnect', {
        method: 'POST',
        body: JSON.stringify({ name }),
        headers: { 'Content-Type': 'application/json' },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['acp'] })
    },
  })
}

export const useRegister = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { name: string; command: string; args?: string[]; credentials_ref?: string | null }) =>
      apiFetch<{ status: string; name: string }>('/api/acp/register', {
        method: 'POST',
        body: JSON.stringify(payload),
        headers: { 'Content-Type': 'application/json' },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['acp'] })
    },
  })
}

export const useDeleteAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ status: string; name: string }>(`/api/acp/${encodeURIComponent(name)}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['acp'] })
    },
  })
}
