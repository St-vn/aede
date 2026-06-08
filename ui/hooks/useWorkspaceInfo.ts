import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface WorkspaceInfo {
  cwd: string
  git_root: string | null
  project_name: string | null
  has_project: boolean
}

export const useWorkspaceInfo = () =>
  useQuery<WorkspaceInfo>({
    queryKey: ['workspaceInfo'],
    queryFn: () => apiFetch<WorkspaceInfo>('/api/workspace/info'),
    staleTime: 60_000,
  })
