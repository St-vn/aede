import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface WorkspaceInfo {
  cwd: string
  git_root: string | null
  project_name: string | null
  has_project: boolean
}

export const useWorkspaceInfo = (sessionId?: string | null, projectDir?: string | null) =>
  useQuery<WorkspaceInfo>({
    queryKey: ['workspaceInfo', sessionId, projectDir],
    queryFn: () => {
      const params = new URLSearchParams()
      if (sessionId) params.set('session_id', sessionId)
      if (projectDir) params.set('project_dir', projectDir)
      const qs = params.toString()
      return apiFetch<WorkspaceInfo>(`/api/workspace/info${qs ? `?${qs}` : ''}`)
    },
    staleTime: 60_000,
    enabled: !!sessionId || !!projectDir,
  })
