import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export const useWorkspaceFiles = (sessionId?: string | null) =>
  useQuery<string[]>({
    queryKey: ['workspaceFiles', sessionId],
    queryFn: () => {
      const params = sessionId ? `?session_id=${sessionId}` : ''
      return apiFetch<string[]>(`/api/workspace/files${params}`)
    },
    enabled: !!sessionId,
  })
