import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GateCard } from '../../components/chat/GateCard'

const defaultOptions = [
  { id: 'allow_once', label: 'Allow once', key: 'a' },
  { id: 'allow_session', label: 'Allow for session', key: 's' },
  { id: 'allow_project', label: 'Allow for project', key: 'p' },
  { id: 'allow_global', label: 'Always allow', key: 'g' },
  { id: 'deny', label: 'Deny', key: 'd' },
  { id: 'redirect', label: 'Redirect', key: 'r' },
]

const props = {
  gateId: 'g_01',
  toolName: 'powershell',
  args: { command: 'rm -rf ./dist' },
  options: defaultOptions,
  onDecision: vi.fn(),
}

test('renders with role=alert', () => {
  render(<GateCard {...props} />)
  expect(screen.getByRole('alert')).toBeInTheDocument()
})

test('shows NEEDS APPROVAL label', () => {
  render(<GateCard {...props} />)
  expect(screen.getByText(/needs approval/i)).toBeInTheDocument()
})

test('shows tool name', () => {
  render(<GateCard {...props} />)
  expect(screen.getByText('powershell')).toBeInTheDocument()
})

test('shows command args', () => {
  render(<GateCard {...props} />)
  expect(screen.getByText(/rm -rf \.\/dist/)).toBeInTheDocument()
})

test('allow-once calls onDecision(allow_once)', () => {
  render(<GateCard {...props} />)
  fireEvent.click(screen.getByRole('button', { name: /allow once/i }))
  expect(props.onDecision).toHaveBeenCalledWith({ gateId: 'g_01', decision: 'allow_once' })
})

test('deny calls onDecision(deny)', () => {
  render(<GateCard {...props} />)
  fireEvent.click(screen.getByRole('button', { name: /^deny$/i }))
  expect(props.onDecision).toHaveBeenCalledWith({ gateId: 'g_01', decision: 'deny' })
})

test('redirect expands input', () => {
  render(<GateCard {...props} />)
  fireEvent.click(screen.getByRole('button', { name: /redirect/i }))
  expect(screen.getByRole('textbox')).toBeInTheDocument()
})
