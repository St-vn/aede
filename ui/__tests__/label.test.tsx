import React from 'react'
import { test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Label } from '../components/ui/label'

test('renders with explicit htmlFor (backward compat)', () => {
  render(<Label htmlFor="my-input">Name</Label>)
  const label = screen.getByText('Name')
  expect(label.tagName).toBe('LABEL')
  expect(label).toHaveAttribute('for', 'my-input')
})

test('auto-associates with wrapped input via useId', () => {
  render(
    <Label>
      <input data-testid="wrapped-input" />
    </Label>
  )
  const label = screen.getByTestId('wrapped-input').closest('label')!
  const input = screen.getByTestId('wrapped-input')
  expect(label).toHaveAttribute('for')
  expect(input).toHaveAttribute('id')
  expect(label.getAttribute('for')).toBe(input.getAttribute('id'))
})

test('renders without crash when no child control and no htmlFor', () => {
  render(<Label>Just text</Label>)
  const label = screen.getByText('Just text')
  expect(label.tagName).toBe('LABEL')
  expect(label).not.toHaveAttribute('for')
})
