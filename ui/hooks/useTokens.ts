import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

interface TokenTurn {
  turn_number: number
  input_tokens: number
  output_tokens: number
  cached_tokens: number
  role: string
  created_at: number
}

interface TokenDetail {
  turns: TokenTurn[]
  totals: { input_tokens: number; output_tokens: number; cached_tokens: number }
  estimated_cost_usd: number | null
  model: string
}

export const useSessionTokens = (sessionId: string | null) =>
  useQuery({
    queryKey: ['tokens', sessionId],
    queryFn: () => apiFetch<TokenDetail>(`/api/sessions/${sessionId}/tokens`),
    enabled: !!sessionId,
  })
