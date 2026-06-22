import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch, apiUpload } from '@/lib/api'

export interface AgentInfo {
  name: string
  description: string
  model: string
  skills: string[]
  tools: string[] | null
  disallowed_tools: string[]
  max_turns: number
  system_prompt: string
  body: string
  file_path: string
  scope: string
}

export const useAgents = () =>
  useQuery({
    queryKey: ['agents'],
    queryFn: () => apiFetch<AgentInfo[]>('/api/agents'),
  })

export const useCreateAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch('/api/agents', { method: 'POST', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })
}

export const useUpdateAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, ...payload }: Record<string, unknown>) =>
      apiFetch(`/api/agents/${encodeURIComponent(name as string)}`, { method: 'PUT', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })
}

export const useUploadAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) =>
      apiUpload('/api/agents/upload', file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })
}

export const useDeleteAgent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, scope, project_dir }: { name: string; scope?: string; project_dir?: string }) =>
      apiFetch(`/api/agents/${encodeURIComponent(name)}?scope=${scope || 'global'}${project_dir ? `&project_dir=${encodeURIComponent(project_dir)}` : ''}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })
}
