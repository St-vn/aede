import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
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

test('shows spinning loader while streaming', () => {
  const { container } = render(<AssistantMessage content="hello" isStreaming={true} />)
  expect(container.querySelector('.animate-spin')).not.toBeNull()
})

test('no spinner when not streaming', () => {
  const { container } = render(<AssistantMessage content="done" isStreaming={false} />)
  expect(container.querySelector('.animate-spin')).toBeNull()
})

test('has aria-live on streaming region', () => {
  const { container } = render(<AssistantMessage content="hi" isStreaming={true} />)
  expect(container.querySelector('[aria-live="polite"]')).not.toBeNull()
})

test('has a copy button that writes content to clipboard', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.assign(navigator, { clipboard: { writeText } })
  render(<AssistantMessage content="hello world" isStreaming={false} />)
  fireEvent.click(screen.getByRole('button', { name: /copy assistant message/i }))
  expect(writeText).toHaveBeenCalledWith('hello world')
})

test('long non-streaming message collapses with Show more button', () => {
  const long = 'line\n'.repeat(20)
  render(<AssistantMessage content={long} isStreaming={false} />)
  expect(screen.getByRole('button', { name: /show more/i })).toBeInTheDocument()
})

test('streaming message does not collapse even if long', () => {
  const long = 'line\n'.repeat(20)
  render(<AssistantMessage content={long} isStreaming={true} />)
  expect(screen.queryByRole('button', { name: /show more/i })).not.toBeInTheDocument()
})
