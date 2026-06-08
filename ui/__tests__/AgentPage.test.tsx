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

test('clicking session loads messages', async () => {
  vi.mocked(apiFetch)
    .mockResolvedValueOnce([sess])  // sessions list
    .mockResolvedValueOnce([])      // messages for s1
  render(<AgentPage />, { wrapper: Wrapper })
  await waitFor(() => screen.getByText('debug session'))
  fireEvent.click(screen.getByText('debug session'))
  await waitFor(() => expect(apiFetch).toHaveBeenCalledWith('/api/sessions/s1/messages'))
})

test('new session button shows empty state', async () => {
  vi.mocked(apiFetch).mockResolvedValue([sess])
  render(<AgentPage />, { wrapper: Wrapper })
  await waitFor(() => screen.getByText('debug session'))
  fireEvent.click(screen.getByRole('button', { name: /new session/i }))
  await waitFor(() => screen.getByText(/your building room/i))
})
