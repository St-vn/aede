import React from 'react'
import { vi, test, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { InputBar } from '../../components/input/InputBar'

let qc: QueryClient

beforeEach(() => {
  qc = new QueryClient({ defaultOptions: { queries: { retry: 0 } } })
})

function renderWithQC(ui: React.ReactElement) {
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

test('textarea has aria-label', () => {
  renderWithQC(<InputBar onSend={vi.fn()} disabled={false} />)
  expect(screen.getByRole('textbox', { name: /message/i })).toBeInTheDocument()
})

test('send button has aria-label', () => {
  renderWithQC(<InputBar onSend={vi.fn()} disabled={false} />)
  expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
})

test('disabled state disables textarea and send button', () => {
  renderWithQC(<InputBar onSend={vi.fn()} disabled={true} />)
  expect(screen.getByRole('textbox')).toBeDisabled()
  expect(screen.getByRole('button', { name: /send message/i })).toBeDisabled()
})

test('Enter key calls onSend', () => {
  const onSend = vi.fn()
  renderWithQC(<InputBar onSend={onSend} disabled={false} />)
  const ta = screen.getByRole('textbox')
  fireEvent.change(ta, { target: { value: 'hello' } })
  fireEvent.keyDown(ta, { key: 'Enter', shiftKey: false })
  expect(onSend).toHaveBeenCalledWith('hello', 'claude-sonnet-4')
})

test('shows stop button while streaming and calls onStop', () => {
  const onStop = vi.fn()
  renderWithQC(<InputBar onSend={vi.fn()} onStop={onStop} isStreaming={true} />)
  const stopBtn = screen.getByRole('button', { name: /stop generating/i })
  expect(stopBtn).toBeInTheDocument()
  fireEvent.click(stopBtn)
  expect(onStop).toHaveBeenCalled()
})

test('queues message when streaming', () => {
  const onSend = vi.fn()
  const onQueue = vi.fn()
  renderWithQC(<InputBar onSend={onSend} onQueue={onQueue} isStreaming={true} />)
  const ta = screen.getByRole('textbox')
  fireEvent.change(ta, { target: { value: 'next' } })
  fireEvent.keyDown(ta, { key: 'Enter', shiftKey: false })
  expect(onQueue).toHaveBeenCalledWith('next')
  expect(onSend).not.toHaveBeenCalled()
})

test('during streaming, both stop and queue send buttons are visible', () => {
  renderWithQC(<InputBar onSend={vi.fn()} onStop={vi.fn()} onQueue={vi.fn()} isStreaming={true} />)
  expect(screen.getByRole('button', { name: /stop generating/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /send queued message/i })).toBeInTheDocument()
})

test('queue button is disabled when text is empty', () => {
  renderWithQC(<InputBar onSend={vi.fn()} onQueue={vi.fn()} isStreaming={true} />)
  expect(screen.getByRole('button', { name: /send queued message/i })).toBeDisabled()
})

test('queue button is enabled when text is present', () => {
  renderWithQC(<InputBar onSend={vi.fn()} onQueue={vi.fn()} isStreaming={true} />)
  const ta = screen.getByRole('textbox')
  fireEvent.change(ta, { target: { value: 'queued' } })
  expect(screen.getByRole('button', { name: /send queued message/i })).not.toBeDisabled()
})

test('clicking queue button calls onQueue with the text', () => {
  const onQueue = vi.fn()
  renderWithQC(<InputBar onSend={vi.fn()} onQueue={onQueue} isStreaming={true} />)
  const ta = screen.getByRole('textbox')
  fireEvent.change(ta, { target: { value: 'queued msg' } })
  fireEvent.click(screen.getByRole('button', { name: /send queued message/i }))
  expect(onQueue).toHaveBeenCalledWith('queued msg')
})

test('during streaming, Enter still queues (regression check)', () => {
  const onQueue = vi.fn()
  renderWithQC(<InputBar onSend={vi.fn()} onQueue={onQueue} isStreaming={true} />)
  const ta = screen.getByRole('textbox')
  fireEvent.change(ta, { target: { value: 'hello' } })
  fireEvent.keyDown(ta, { key: 'Enter', shiftKey: false })
  expect(onQueue).toHaveBeenCalledWith('hello')
})
