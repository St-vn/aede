import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CodeBlock } from '../../components/chat/CodeBlock'

// Mock Shiki — WASM not available in test env
vi.mock('shiki', () => ({
  createHighlighter: vi.fn().mockResolvedValue({
    codeToHtml: vi.fn().mockReturnValue('<pre>highlighted</pre>'),
  }),
}))

test('renders language label', () => {
  render(<CodeBlock language="python" code="print('hello')" />)
  expect(screen.getByText('python')).toBeInTheDocument()
})

test('renders Copy button with aria-label', () => {
  render(<CodeBlock language="python" code="print('hello')" />)
  expect(screen.getByRole('button', { name: /copy code/i })).toBeInTheDocument()
})

test('unknown language renders "text" label', () => {
  render(<CodeBlock language={undefined} code="raw stuff" />)
  expect(screen.getByText('text')).toBeInTheDocument()
})

test('Copy button copies code to clipboard and shows check/copied state', async () => {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
    writable: true,
  })
  render(<CodeBlock language="ts" code="const x = 1" />)
  const btn = screen.getByRole('button', { name: /copy code/i })
  fireEvent.click(btn)
  await waitFor(() => {
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("const x = 1")
  })
})
