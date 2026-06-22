import React from 'react'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EmptyState } from '../../components/empty/EmptyState'

// Mock apiFetch so useProjects (and any other hooks) don't hit a real server.
vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(async (path: string) => {
    if (path === '/api/projects') return []
    return {}
  }),
  API_BASE: 'http://localhost:8000',
  WS_BASE: 'ws://localhost:8000',
}))

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

test('renders subtitle', () => {
  renderWithClient(<EmptyState />)
  expect(screen.getByText(/aede, your building room/i)).toBeInTheDocument()
})

test('does not render image when config.image is null', () => {
  renderWithClient(<EmptyState />)
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
})
