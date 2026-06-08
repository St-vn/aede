import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface Session {
  id: string
  title: string
  model: string
  parent_id: string | null
  created_at: string
  project_dir?: string | null
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  is_branch_point?: boolean
}

export const useSessions = () =>
  useQuery({ queryKey: ['sessions'], queryFn: () => apiFetch<Session[]>('/api/sessions') })

export const useSessionMessages = (sessionId: string | null) =>
  useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () => apiFetch<Message[]>(`/api/sessions/${sessionId}/messages`),
    enabled: !!sessionId,
  })

export const useCreateSession = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ model, parentId, projectDir }: { model: string; parentId?: string; projectDir?: string }) =>
      apiFetch<Session>('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, parent_id: parentId, project_dir: projectDir }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  })
}

export const useDeleteSession = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch(`/api/sessions/${sessionId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  })
}

export const useRenameSession = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      apiFetch<Session>(`/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  })
}
