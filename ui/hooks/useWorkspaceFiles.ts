import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export const useWorkspaceFiles = () =>
  useQuery<string[]>({
    queryKey: ['workspaceFiles'],
    queryFn: () => apiFetch<string[]>('/api/workspace/files'),
  })
