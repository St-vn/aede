import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch, apiUpload } from '@/lib/api'

export interface SkillInfo {
  name: string
  description: string
  trigger_phrases: string[]
  allowed_tools: string[] | null
  model: string | null
  body: string
  file_path: string
  scope: string
}

export const useSkills = () =>
  useQuery({
    queryKey: ['skills'],
    queryFn: () => apiFetch<SkillInfo[]>('/api/skills'),
  })

export const useCreateSkill = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch('/api/skills', { method: 'POST', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skills'] }),
  })
}

export const useUpdateSkill = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, ...payload }: Record<string, unknown>) =>
      apiFetch(`/api/skills/${encodeURIComponent(name as string)}`, { method: 'PUT', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skills'] }),
  })
}

export const useUploadSkill = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) =>
      apiUpload('/api/skills/upload', file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skills'] }),
  })
}

export const useDeleteSkill = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, scope, project_dir }: { name: string; scope?: string; project_dir?: string }) =>
      apiFetch(`/api/skills/${encodeURIComponent(name)}?scope=${scope || 'global'}${project_dir ? `&project_dir=${encodeURIComponent(project_dir)}` : ''}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skills'] }),
  })
}
