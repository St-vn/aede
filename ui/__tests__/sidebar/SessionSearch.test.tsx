import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SessionSearch } from '../../components/sidebar/SessionSearch'

const sessions = [
  { id: 's1', title: 'debug router', model: 'sonnet', parent_id: null, created_at: new Date().toISOString() },
  { id: 's2', title: 'research codex', model: 'sonnet', parent_id: null, created_at: new Date().toISOString() },
]

vi.mock('@/hooks/useSession', () => ({
  useRenameSession: () => ({
    mutate: vi.fn(),
  }),
}))

test('shows all sessions by default', () => {
  render(<SessionSearch sessions={sessions} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(screen.getByText('debug router')).toBeInTheDocument()
  expect(screen.getByText('research codex')).toBeInTheDocument()
})

test('filters sessions by keyword (case-insensitive)', () => {
  render(<SessionSearch sessions={sessions} onSelect={vi.fn()} onDelete={vi.fn()} />)
  fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'DEBUG' } })
  expect(screen.getByText('debug router')).toBeInTheDocument()
  expect(screen.queryByText('research codex')).not.toBeInTheDocument()
})

test('clears filter when input emptied', () => {
  render(<SessionSearch sessions={sessions} onSelect={vi.fn()} onDelete={vi.fn()} />)
  fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'debug' } })
  fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: '' } })
  expect(screen.getByText('research codex')).toBeInTheDocument()
})

test('search input has aria-label', () => {
  render(<SessionSearch sessions={sessions} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(screen.getByRole('searchbox')).toBeInTheDocument()
})

test('shows empty state message when sessions list is empty', () => {
  render(<SessionSearch sessions={[]} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(screen.getByText(/no sessions/i)).toBeInTheDocument()
})

test('shows search-specific message when query matches nothing', () => {
  const sessions = [{ id: '1', title: 'hello', model: 'x', parent_id: null, created_at: '2024-01-01' }]
  render(<SessionSearch sessions={sessions} onSelect={vi.fn()} onDelete={vi.fn()} />)
  fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'zzz' } })
  expect(screen.getByText(/no sessions match/i)).toBeInTheDocument()
})
