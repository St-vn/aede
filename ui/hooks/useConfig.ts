import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface ConfigSources {
  [key: string]: string
}

export interface AedeConfig {
  model: string
  context_window: number
  compaction_threshold: number
  tool_output_max_tokens: number
  shell: string
  wsl_distro: string
  batch_approval_max: number
  auto_approve: string[]
  api_base_url: string | null
  grounding_enabled: boolean
  critic_enabled: boolean
  critic_model: string | null
  critic_api_base_url: string | null
  ollama_base_url: string
  ollama_embed_model: string
  ollama_timeout_s: number
  learnings_top_k: number
  learnings_max_tokens: number
  reasoning_effort: string
  thinking_budget: number
  model_prices: Record<string, unknown>
  mcp_servers: Record<string, unknown>
}

export const useConfig = () =>
  useQuery({
    queryKey: ['config'],
    queryFn: () => apiFetch<AedeConfig>('/api/config'),
  })

export const useConfigSources = () =>
  useQuery({
    queryKey: ['config', 'sources'],
    queryFn: () => apiFetch<ConfigSources>('/api/config/sources'),
  })

export const useUpdateConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, value, scope, projectDir }: { key: string; value: string; scope?: string; projectDir?: string }) =>
      apiFetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value, scope: scope || 'global', project_dir: projectDir }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] })
    },
  })
}
