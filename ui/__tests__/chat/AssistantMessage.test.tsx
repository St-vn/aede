import React from 'react'
import { render, screen } from '@testing-library/react'
import { AssistantMessage } from '../../components/chat/AssistantMessage'

test('renders markdown bold', () => {
  render(<AssistantMessage content="**bold text**" isStreaming={false} />)
  const bold = screen.getByText('bold text')
  expect(bold.tagName).toBe('STRONG')
})

test('renders markdown header', () => {
  render(<AssistantMessage content="## Heading" isStreaming={false} />)
  expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument()
})

test('shows blinking cursor while streaming', () => {
  const { container } = render(<AssistantMessage content="hello" isStreaming={true} />)
  expect(container.textContent).toContain('▌')
})

test('no cursor when not streaming', () => {
  const { container } = render(<AssistantMessage content="done" isStreaming={false} />)
  expect(container.textContent).not.toContain('▌')
})

test('has aria-live on streaming region', () => {
  const { container } = render(<AssistantMessage content="hi" isStreaming={true} />)
  expect(container.querySelector('[aria-live="polite"]')).not.toBeNull()
})
