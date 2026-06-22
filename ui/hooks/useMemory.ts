import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

interface Learning {
  id: string
  content: string
  type: string
  source: string
  created_at: number
  trusted: boolean
}

export const useLearnings = () =>
  useQuery({
    queryKey: ['learnings'],
    queryFn: () => apiFetch<Learning[]>('/api/learnings'),
  })

export const useAddLearning = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ content, type }: { content: string; type?: string }) =>
      apiFetch<Learning>('/api/learnings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, type: type || 'config-correction', source: 'user', source_session_id: '', trusted: true }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['learnings'] }),
  })
}

export const useDeleteLearning = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (learningId: string) =>
      apiFetch(`/api/learnings/${learningId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['learnings'] }),
  })
}
