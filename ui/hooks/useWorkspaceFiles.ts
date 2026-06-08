import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export const useWorkspaceFiles = (sessionId?: string | null, projectDir?: string | null) =>
  useQuery<string[]>({
    queryKey: ['workspaceFiles', sessionId, projectDir],
    queryFn: () => {
      const params = new URLSearchParams()
      if (sessionId) params.set('session_id', sessionId)
      if (projectDir) params.set('project_dir', projectDir)
      const qs = params.toString()
      return apiFetch<string[]>(`/api/workspace/files${qs ? `?${qs}` : ''}`)
    },
    enabled: !!sessionId || !!projectDir,
  })
