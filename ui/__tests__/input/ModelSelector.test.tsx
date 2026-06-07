import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ModelSelector } from '../../components/input/ModelSelector'

test('shows current model name', () => {
  render(<ModelSelector currentModel="claude-sonnet-4" onModelChange={vi.fn()} />)
  expect(screen.getByText(/sonnet/i)).toBeInTheDocument()
})

test('dropdown lists Opus and Haiku options', async () => {
  render(<ModelSelector currentModel="claude-sonnet-4" onModelChange={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: /select model/i }))
  expect(await screen.findByText(/opus/i)).toBeInTheDocument()
  expect(await screen.findByText(/haiku/i)).toBeInTheDocument()
})

test('selecting a model calls onModelChange', async () => {
  const onChange = vi.fn()
  render(<ModelSelector currentModel="claude-sonnet-4" onModelChange={onChange} />)
  fireEvent.click(screen.getByRole('button', { name: /select model/i }))
  fireEvent.click(await screen.findByText(/haiku/i))
  expect(onChange).toHaveBeenCalledWith(expect.stringContaining('haiku'))
})
