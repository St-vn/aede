import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Sidebar } from '../../components/sidebar/Sidebar'

vi.mock('@/lib/api', () => ({
  API_BASE: 'http://test',
  WS_BASE: 'ws://test',
  apiFetch: vi.fn(),
}))

const qc = new QueryClient({ defaultOptions: { queries: { retry: 0 } } })
function Wrapper({ children }: any) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const props = {
  activeSessionId: null,
  onSelectSession: vi.fn(),
  onNewSession: vi.fn(),
}

test('opens with brand label visible', () => {
  render(<Sidebar {...props} />, { wrapper: Wrapper })
  expect(screen.getByText('aede')).toBeVisible()
})

test('collapse hides brand label', () => {
  render(<Sidebar {...props} />, { wrapper: Wrapper })
  fireEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
  expect(screen.queryByText('aede')).not.toBeInTheDocument()
})

test('expand after collapse restores label', () => {
  render(<Sidebar {...props} />, { wrapper: Wrapper })
  fireEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
  fireEvent.click(screen.getByRole('button', { name: /expand sidebar/i }))
  expect(screen.getByText('aede')).toBeVisible()
})

test('toggle button has aria-label', () => {
  render(<Sidebar {...props} />, { wrapper: Wrapper })
  const btn = screen.getByRole('button', { name: /collapse sidebar|expand sidebar/i })
  expect(btn).toHaveAttribute('aria-label')
})

test('new session button is present', () => {
  render(<Sidebar {...props} />, { wrapper: Wrapper })
  expect(screen.getByRole('button', { name: /new session/i })).toBeInTheDocument()
})

test('profile and settings buttons have aria-labels', () => {
  render(<Sidebar {...props} />, { wrapper: Wrapper })
  expect(screen.getByRole('button', { name: /profile/i })).toHaveAttribute('aria-label')
  expect(screen.getByRole('button', { name: /settings/i })).toHaveAttribute('aria-label')
})
