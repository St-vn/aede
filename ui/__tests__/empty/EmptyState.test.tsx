import React from 'react'
import { render, screen } from '@testing-library/react'
import { EmptyState } from '../../components/empty/EmptyState'

test('renders subtitle', () => {
  render(<EmptyState />)
  expect(screen.getByText(/aede, your building room/i)).toBeInTheDocument()
})

test('does not render image when config.image is null', () => {
  render(<EmptyState />)
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
})
