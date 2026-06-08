import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { InputBar } from '../../components/input/InputBar'

test('textarea has aria-label', () => {
  render(<InputBar onSend={vi.fn()} disabled={false} />)
  expect(screen.getByRole('textbox', { name: /message/i })).toBeInTheDocument()
})

test('send button has aria-label', () => {
  render(<InputBar onSend={vi.fn()} disabled={false} />)
  expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
})

test('disabled state disables textarea and send button', () => {
  render(<InputBar onSend={vi.fn()} disabled={true} />)
  expect(screen.getByRole('textbox')).toBeDisabled()
  expect(screen.getByRole('button', { name: /send message/i })).toBeDisabled()
})

test('Enter key calls onSend', () => {
  const onSend = vi.fn()
  render(<InputBar onSend={onSend} disabled={false} />)
  const ta = screen.getByRole('textbox')
  fireEvent.change(ta, { target: { value: 'hello' } })
  fireEvent.keyDown(ta, { key: 'Enter', shiftKey: false })
  expect(onSend).toHaveBeenCalledWith('hello', 'claude-sonnet-4')
})
