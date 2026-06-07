import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SessionRow } from '../../components/sidebar/SessionRow'

const sess = {
  id: 's1', title: 'debug the router', model: 'claude-sonnet-4',
  parent_id: null, created_at: new Date(Date.now() - 7200000).toISOString(),
}

vi.mock('@/hooks/useSession', () => ({
  useRenameSession: () => ({
    mutate: vi.fn(),
  }),
}))

test('renders title', () => {
  render(<SessionRow session={sess} isActive={false} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(screen.getByText(/debug the router/i)).toBeInTheDocument()
})

test('active row has data-active=true', () => {
  const { container } = render(<SessionRow session={sess} isActive={true} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(container.querySelector('[data-active="true"]')).not.toBeNull()
})

test('inactive row does not have data-active=true', () => {
  const { container } = render(<SessionRow session={sess} isActive={false} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(container.querySelector('[data-active="true"]')).toBeNull()
})

test('branch row renders ┆ glyph', () => {
  const child = { ...sess, id: 's2', parent_id: 's1' }
  render(<SessionRow session={child} isActive={false} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(screen.getByText('┆')).toBeInTheDocument()
})

test('root row has no ┆ glyph', () => {
  render(<SessionRow session={sess} isActive={false} onSelect={vi.fn()} onDelete={vi.fn()} />)
  expect(screen.queryByText('┆')).not.toBeInTheDocument()
})

test('onSelect called on click', () => {
  const onSelect = vi.fn()
  render(<SessionRow session={sess} isActive={false} onSelect={onSelect} onDelete={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: /debug the router/i }))
  expect(onSelect).toHaveBeenCalledWith('s1')
})

test('row is keyboard focusable', () => {
  render(<SessionRow session={sess} isActive={false} onSelect={vi.fn()} onDelete={vi.fn()} />)
  const btn = screen.getByRole('button', { name: /debug the router/i })
  expect(btn.tabIndex).not.toBe(-1)
})
