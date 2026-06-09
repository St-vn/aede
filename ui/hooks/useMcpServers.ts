import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface McpToolInfo {
  name: string
  description?: string
  inputSchema?: Record<string, unknown>
}

export interface McpServerInfo {
  name: string
  command: string
  args: string[]
  env?: Record<string, string> | null
  url?: string
  trusted?: boolean
  status?: string
  enabled?: boolean
  disabled_tools?: string[]
  tools?: McpToolInfo[]
}

export const useMcpServers = () =>
  useQuery({
    queryKey: ['mcp', 'servers'],
    queryFn: () => apiFetch<Record<string, McpServerInfo>>('/api/mcp/servers'),
  })

export const useAddMcpServer = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch('/api/mcp/servers', { method: 'POST', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mcp', 'servers'] }),
  })
}

export const useUpdateMcpServer = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch('/api/mcp/servers', { method: 'POST', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mcp', 'servers'] }),
  })
}

export const useDeleteMcpServer = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch(`/api/mcp/servers/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mcp', 'servers'] }),
  })
}

export const useRestartMcpServers = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch('/api/mcp/servers/restart', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mcp', 'servers'] }),
  })
}
