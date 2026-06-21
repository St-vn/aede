import React from 'react'
import { vi, test, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ModelSelector } from '../../components/input/ModelSelector'

// Mock apiFetch so useModels / useConfig don't hit a real server.
// /api/models returns two models; /api/config returns a minimal config.
vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(async (path: string) => {
    if (path === '/api/models') {
      return [
        { id: 'claude-opus-4', label: 'Claude Opus 4', provider: 'anthropic' },
        { id: 'claude-haiku-3-5', label: 'Claude Haiku 3.5', provider: 'anthropic' },
        { id: 'claude-sonnet-4', label: 'Claude Sonnet 4', provider: 'anthropic' },
      ]
    }
    if (path === '/api/config') {
      return { reasoning_effort: 'auto', thinking_budget: 0 }
    }
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

beforeEach(() => {
  vi.clearAllMocks()
})

test('shows current model name', async () => {
  renderWithClient(<ModelSelector currentModel="claude-sonnet-4" onModelChange={vi.fn()} />)
  // The button label shows the current model's label; wait for data to arrive.
  expect(await screen.findByText(/sonnet/i)).toBeInTheDocument()
})

test('dropdown lists Opus and Haiku options', async () => {
  renderWithClient(<ModelSelector currentModel="claude-sonnet-4" onModelChange={vi.fn()} />)
  fireEvent.click(await screen.findByRole('button', { name: /select model/i }))
  expect(await screen.findByText(/opus/i)).toBeInTheDocument()
  expect(await screen.findByText(/haiku/i)).toBeInTheDocument()
})

test('selecting a model calls onModelChange', async () => {
  const onChange = vi.fn()
  renderWithClient(<ModelSelector currentModel="claude-sonnet-4" onModelChange={onChange} />)
  fireEvent.click(await screen.findByRole('button', { name: /select model/i }))
  fireEvent.click(await screen.findByText(/haiku/i))
  expect(onChange).toHaveBeenCalledWith(expect.stringContaining('haiku'))
})
