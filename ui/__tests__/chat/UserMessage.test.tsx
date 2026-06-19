import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { vi, test, expect } from 'vitest'
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

test('copy button writes raw message text to clipboard', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.assign(navigator, { clipboard: { writeText } })
  render(<UserMessage content="hello world" timestamp={new Date().toISOString()} />)
  fireEvent.click(screen.getByRole('button', { name: /copy message/i }))
  expect(writeText).toHaveBeenCalledWith('hello world')
})

const long = 'line\n'.repeat(20)

test('long message collapses and shows Show more', () => {
  render(<UserMessage content={long} timestamp={new Date().toISOString()} />)
  expect(screen.getByRole('button', { name: /show more/i })).toBeInTheDocument()
})

test('clicking Show more expands and shows Show less', () => {
  render(<UserMessage content={long} timestamp={new Date().toISOString()} />)
  fireEvent.click(screen.getByRole('button', { name: /show more/i }))
  expect(screen.getByRole('button', { name: /show less/i })).toBeInTheDocument()
})

test('can open collapsed message in modal', () => {
  render(<UserMessage content={'x'.repeat(2000)} timestamp={new Date().toISOString()} />)
  fireEvent.click(screen.getByRole('button', { name: /open in modal/i }))
  expect(screen.getByRole('dialog')).toHaveTextContent('x'.repeat(2000))
})

test('rewind menu offers conversation and code options', () => {
  const onRewind = vi.fn()
  render(<UserMessage content="do x" messageId="m1" onRewind={onRewind} timestamp={new Date().toISOString()} />)
  fireEvent.click(screen.getByRole('button', { name: /rewind/i }))
  fireEvent.click(screen.getByText(/rewind conversation only/i))
  expect(onRewind).toHaveBeenCalledWith('m1', { revertCode: false })
})

test('all action buttons have aria-labels', () => {
  render(<UserMessage content={'x'.repeat(900)} messageId="m1" onRewind={vi.fn()} timestamp={new Date().toISOString()} />)
  expect(screen.getByRole('button', { name: /copy message/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /rewind/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /show more/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /open in modal/i })).toBeInTheDocument()
})

test('has aria-live region for screen reader copy feedback', () => {
  render(<UserMessage content="hello" timestamp={new Date().toISOString()} />)
  const liveRegion = document.querySelector('[aria-live="polite"]')
  expect(liveRegion).toBeInTheDocument()
  expect(liveRegion).toHaveClass('sr-only')
})
