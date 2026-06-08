import React from 'react'
import { render, screen } from '@testing-library/react'
import { UserMessage } from '../../components/chat/UserMessage'

test('renders message content', () => {
  render(<UserMessage content="hello world" timestamp={new Date().toISOString()} />)
  expect(screen.getByText('hello world')).toBeInTheDocument()
})

test('bubble has muted background', () => {
  const { container } = render(<UserMessage content="hi" timestamp={new Date().toISOString()} />)
  const bubble = container.querySelector('.bg-muted')
  expect(bubble).not.toBeNull()
})
