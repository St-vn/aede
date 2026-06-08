import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface Project {
  id: string
  project_dir: string
  display_name: string
  created_at: number
  updated_at: number
}

export const useProjects = () =>
  useQuery({ queryKey: ['projects'], queryFn: () => apiFetch<Project[]>('/api/projects') })

export const useAddProject = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (path: string) =>
      apiFetch<Project>('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export const useRemoveProject = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) =>
      apiFetch(`/api/projects/${projectId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export const useDeleteProjectFolder = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) =>
      apiFetch(`/api/projects/${projectId}/delete-folder`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export const useRemoveProjectRepo = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) =>
      apiFetch(`/api/projects/${projectId}/remove-git`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}
