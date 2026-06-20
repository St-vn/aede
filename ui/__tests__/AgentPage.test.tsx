import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('@/lib/api', () => ({
  API_BASE: 'http://test',
  WS_BASE: 'ws://test',
  apiFetch: vi.fn(),
}))

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ send: vi.fn() })
}))

import { AgentPage } from '../app/app/AgentPage'
import { apiFetch } from '@/lib/api'

const sess = {
  id: 's1', title: 'debug session', model: 'claude-sonnet-4',
  parent_id: null, created_at: new Date().toISOString()
}

function Wrapper({ children }: any) {
  return (
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: 0 } } })}>
      {children}
    </QueryClientProvider>
  )
}

// Route apiFetch by URL so every query in the (large) component tree resolves
// to a sane default. A bare mockResolvedValueOnce chain breaks the moment a new
// query (useSoul, useSkills, useAgents, useMcpServers, useModels, ...) is added
// to the tree, since unmatched calls then resolve to undefined and crash on
// `.then`/`.slice`. Tests override specific endpoints via `routes`.
const sessionsResponse = {
  projects: {} as Record<string, unknown>,
  global: { sessions: [sess], total: 1, limit: 50, offset: 0, has_more: false },
}

function mockApi(routes: Record<string, unknown> = {}) {
  vi.mocked(apiFetch).mockImplementation(async (path: string) => {
    for (const [prefix, value] of Object.entries(routes)) {
      if (path === prefix || path.startsWith(prefix)) return value as any
    }
    // GET /api/sessions returns the grouped {projects, global} shape; the POST
    // path and the /messages sub-path are handled by `routes` overrides.
    if (path === '/api/sessions' || path.startsWith('/api/sessions?')) {
      return sessionsResponse as any
    }
    if (path.startsWith('/api/config')) return {} as any
    if (path.startsWith('/api/soul')) return {} as any
    // Skills/agents/models/projects are list-shaped; mcp servers object-shaped.
    if (path.startsWith('/api/mcp')) return {} as any
    return [] as any
  })
}

test('clicking session loads messages', async () => {
  mockApi({ '/api/sessions/s1/messages': [] })
  render(<AgentPage />, { wrapper: Wrapper })
  await waitFor(() => screen.getByText('debug session'))
  fireEvent.click(screen.getByText('debug session'))
  await waitFor(() => expect(apiFetch).toHaveBeenCalledWith('/api/sessions/s1/messages'))
})

test('new session button shows empty state', async () => {
  mockApi()
  render(<AgentPage />, { wrapper: Wrapper })
  await waitFor(() => screen.getByText('debug session'))
  fireEvent.click(screen.getByRole('button', { name: /new session/i }))
  await waitFor(() => screen.getByText(/your building room/i))
})
