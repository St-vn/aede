import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

interface Credential {
  name: string
  provider: string | null
  updated_at: string
}

export const useCredentials = () =>
  useQuery({
    queryKey: ['credentials'],
    queryFn: () => apiFetch<Credential[]>('/api/credentials'),
  })

export const useAddCredential = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, value, provider }: { name: string; value: string; provider?: string }) =>
      apiFetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, value, provider }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['credentials'] })
      qc.invalidateQueries({ queryKey: ['acp'] })
    },
  })
}

export const useDeleteCredential = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch(`/api/credentials/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['credentials'] })
      qc.invalidateQueries({ queryKey: ['acp'] })
    },
  })
}
