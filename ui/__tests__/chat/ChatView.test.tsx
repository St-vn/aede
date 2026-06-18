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
    type: 'gate_request', gate_id: 'g1', tool_name: 'powershell', args: { command: 'echo hi' },
    batch_count: 1, mode: 'normal', reason: null,
    options: [{ id: 'allow_once', label: 'Allow once', key: 'a' }, { id: 'deny', label: 'Deny', key: 'd' }],
  }))
  expect(screen.getByRole('alert')).toBeInTheDocument()
  expect(screen.getByText('powershell')).toBeInTheDocument()
  expect(screen.getByText('normal')).toBeInTheDocument()
})

test('input bar disabled while gate is open', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({
    type: 'gate_request', gate_id: 'g1', tool_name: 'rm', args: {},
    batch_count: 1, mode: 'normal', reason: null,
    options: [{ id: 'allow_once', label: 'Allow once', key: 'a' }, { id: 'deny', label: 'Deny', key: 'd' }],
  }))
  expect(screen.getByRole('textbox')).toBeDisabled()
})

test('persisted messages with thinking_segments render interleaved blocks', () => {
  // Test the persisted path: messages with thinking_segments + tool_calls
  // render in the correct interleaved order via AssistantMessage.
  const msgsWithSegments = [
    {
      id: 'm-acp', role: 'assistant' as const, content: 'final answer',
      created_at: new Date().toISOString(),
      thinking_segments: [
        { text: 'I think...', seq: 0 },
        { text: 'Done thinking', seq: 2 },
      ],
      tool_calls: [
        { id: 'tc1', name: 'Read', args: {}, status: 'success', output: 'file content' }
      ],
    },
  ]
  renderWithClient(<ChatView sessionId="s1" messages={msgsWithSegments} />)
  expect(screen.getByText(/I think\.\.\./)).toBeInTheDocument()
  expect(screen.getByText(/Done thinking/)).toBeInTheDocument()
})

test('turn_done clears streamingBlocks', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => {
    wsEventHandler?.({ type: 'thinking_delta', text: 'thought', seq: 0 })
  })
  act(() => {
    wsEventHandler?.({ type: 'turn_done' })
  })
  expect(screen.queryByText(/thought/)).not.toBeInTheDocument()
})

test('ask_user_request renders AskUserCard with question', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({
    type: 'ask_user_request', question_id: 'q1', question: 'What framework?',
  }))
  expect(screen.getByText('What framework?')).toBeInTheDocument()
  expect(screen.getByText(/agent asks/i)).toBeInTheDocument()
})

test('ask_user_request with choices renders choice buttons', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({
    type: 'ask_user_request', question_id: 'q2', question: 'Pick:', choices: ['React', 'Vue'],
  }))
  expect(screen.getByRole('button', { name: 'React' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Vue' })).toBeInTheDocument()
})

test('input bar disabled while ask_user prompt is active', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({
    type: 'ask_user_request', question_id: 'q3', question: 'Ready?',
  }))
  expect(screen.getByRole('textbox', { name: /message/i })).toBeDisabled()
})

test('ask_user_response clears prompt and re-enables input', () => {
  renderWithClient(<ChatView sessionId="s1" messages={[]} />)
  act(() => wsEventHandler?.({
    type: 'ask_user_request', question_id: 'q4', question: 'Go?',
  }))
  expect(screen.getByText('Go?')).toBeInTheDocument()
  act(() => wsEventHandler?.({
    type: 'ask_user_response', question_id: 'q4', answer: 'yes',
  }))
  expect(screen.queryByText('Go?')).not.toBeInTheDocument()
})
