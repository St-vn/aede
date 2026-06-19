import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface Session {
  id: string
  title: string
  model: string
  parent_id: string | null
  created_at: string
  project_dir?: string | null
  gate_mode?: string | null
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  is_branch_point?: boolean
  thinking?: string
  thinking_segments?: Array<{ text: string; seq: number }>
  turn_duration_ms?: number | null
}

export interface GlobalSessionsPage {
  sessions: Session[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface SessionsResponse {
  projects: Record<string, Session[]>
  global: GlobalSessionsPage
}

interface UseSessionsParams {
  globalLimit?: number
  globalOffset?: number
}

export const useSessions = (params?: UseSessionsParams) => {
  const sp = new URLSearchParams()
  if (params?.globalLimit) sp.set('global_limit', String(params.globalLimit))
  if (params?.globalOffset) sp.set('global_offset', String(params.globalOffset))
  const qs = sp.toString()
  return useQuery({
    queryKey: ['sessions', params],
    queryFn: () => apiFetch<SessionsResponse>(`/api/sessions${qs ? '?' + qs : ''}`),
  })
}

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

export function useRewind() {
  return {
    rewind: async (sessionId: string, messageId: string, revertCode: boolean) => {
      return apiFetch(`/api/sessions/${sessionId}/rewind`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, revert_code: revertCode }),
      })
    },
  }
}

export const useUpdateSessionMode = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, gateMode }: { sessionId: string; gateMode: string }) =>
      apiFetch<Session>(`/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gate_mode: gateMode }),
      }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.setQueryData(['session', vars.sessionId], (old: Session | undefined) =>
        old ? { ...old, gate_mode: vars.gateMode } : old
      )
    },
  })
}
