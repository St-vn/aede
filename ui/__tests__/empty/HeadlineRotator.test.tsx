import React from 'react'
import { vi, test, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { HeadlineRotator } from '../../components/empty/HeadlineRotator'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

test('renders first headline initially', () => {
  render(<HeadlineRotator headlines={['First', 'Second']} intervalMs={3500} />)
  expect(screen.getByText('First')).toBeInTheDocument()
})

test('rotates to next headline after interval', () => {
  render(<HeadlineRotator headlines={['First', 'Second']} intervalMs={3500} />)
  act(() => {
    vi.advanceTimersByTime(3500)
  })
  expect(screen.getByText('Second')).toBeInTheDocument()
})

test('wraps around after last headline', () => {
  render(<HeadlineRotator headlines={['A', 'B']} intervalMs={1000} />)
  act(() => {
    vi.advanceTimersByTime(1000)
  })
  act(() => {
    vi.advanceTimersByTime(1000)
  })
  expect(screen.getByText('A')).toBeInTheDocument()
})
