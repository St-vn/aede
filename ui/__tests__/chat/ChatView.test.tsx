import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatView } from '../../components/chat/ChatView'

// Mock useWebSocket to return a controllable dispatch
let wsEventHandler: ((ev: any) => void) | null = null
vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: (_id: any, handler: any) => {
    wsEventHandler = handler
    return { send: vi.fn() }
  },
}))

const messages = [
  { id: 'm1', role: 'user' as const, content: 'hello', created_at: new Date().toISOString() },
  { id: 'm2', role: 'assistant' as const, content: 'hi there', created_at: new Date().toISOString() },
]

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  )
}

test('renders existing messages', () => {
  renderWithClient(<ChatView sessionId="s1" messages={messages} />)
  expect(screen.getByText('hello')).toBeInTheDocument()
  expect(screen.getByText(/hi there/)).toBeInTheDocument()
})

test('streaming text_delta appends text with cursor', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({ type: 'text_delta', text: 'Hello ' }))
  act(() => wsEventHandler?.({ type: 'text_delta', text: 'world' }))
  expect(screen.getByText(/Hello world/)).toBeInTheDocument()
  expect(screen.getByText(/▌/)).toBeInTheDocument()
})

test('turn_done removes streaming cursor', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({ type: 'text_delta', text: 'Done' }))
  act(() => wsEventHandler?.({ type: 'turn_done' }))
  expect(screen.queryByText(/▌/)).not.toBeInTheDocument()
})

test('gate_request renders GateCard', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({
    type: 'gate_request', gate_id: 'g1', tool_name: 'powershell', args: { command: 'echo hi' }, batch_count: 1
  }))
  expect(screen.getByRole('alert')).toBeInTheDocument()
})

test('input bar disabled while gate is open', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({
    type: 'gate_request', gate_id: 'g1', tool_name: 'rm', args: {}, batch_count: 1
  }))
  expect(screen.getByRole('textbox')).toBeDisabled()
})
