import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface Model {
  id: string
  label: string
  provider: string
}

export const useModels = () =>
  useQuery({
    queryKey: ['models'],
    queryFn: () => apiFetch<Model[]>('/api/models'),
  })

export const useAddModel = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (model: { id: string; label: string; provider: string }) =>
      apiFetch('/api/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(model),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  })
}

export const useDeleteModel = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/models/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  })
}

export const useUpdateModels = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (models: Model[]) =>
      apiFetch('/api/models', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(models),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  })
}

export const useResetModels = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch('/api/models/reset', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  })
}
