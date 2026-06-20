'use client'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface ToolInfo {
  name: string
  description: string
}

export const useTools = () =>
  useQuery({
    queryKey: ['tools'],
    queryFn: () => apiFetch<ToolInfo[]>('/api/tools'),
  })
