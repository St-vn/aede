import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Sidebar } from '../../components/sidebar/Sidebar'

const props = {
  sessions: [],
  activeSessionId: null,
  onSelectSession: vi.fn(),
  onNewSession: vi.fn(),
}

test('opens with brand label visible', () => {
  render(<Sidebar {...props} />)
  expect(screen.getByText('aede')).toBeVisible()
})

test('collapse hides brand label', () => {
  render(<Sidebar {...props} />)
  fireEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
  expect(screen.queryByText('aede')).not.toBeInTheDocument()
})

test('expand after collapse restores label', () => {
  render(<Sidebar {...props} />)
  fireEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
  fireEvent.click(screen.getByRole('button', { name: /expand sidebar/i }))
  expect(screen.getByText('aede')).toBeVisible()
})

test('toggle button has aria-label', () => {
  render(<Sidebar {...props} />)
  const btn = screen.getByRole('button', { name: /collapse sidebar|expand sidebar/i })
  expect(btn).toHaveAttribute('aria-label')
})

test('new session button is present', () => {
  render(<Sidebar {...props} />)
  expect(screen.getByRole('button', { name: /new session/i })).toBeInTheDocument()
})

test('profile and settings buttons have aria-labels', () => {
  render(<Sidebar {...props} />)
  expect(screen.getByRole('button', { name: /profile/i })).toHaveAttribute('aria-label')
  expect(screen.getByRole('button', { name: /settings/i })).toHaveAttribute('aria-label')
})
