import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface WorkspaceInfo {
  cwd: string
  git_root: string | null
  project_name: string | null
  has_project: boolean
}

export const useWorkspaceInfo = (sessionId?: string | null) =>
  useQuery<WorkspaceInfo>({
    queryKey: ['workspaceInfo', sessionId],
    queryFn: () => {
      const params = sessionId ? `?session_id=${sessionId}` : ''
      return apiFetch<WorkspaceInfo>(`/api/workspace/info${params}`)
    },
    staleTime: 60_000,
    enabled: !!sessionId,
  })
