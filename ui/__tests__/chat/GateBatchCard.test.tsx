import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GateBatchCard } from '../../components/chat/GateBatchCard'

const gates = [
  { gateId: 'g_01', toolName: 'powershell', args: { command: 'rm -rf ./dist' } },
  { gateId: 'g_02', toolName: 'write_file', args: { path: '/etc/hosts', content: '127.0.0.1 foo' } },
  { gateId: 'g_03', toolName: 'create_file', args: { path: '/tmp/test.py', content: 'print(1)' } },
]

test('renders nothing when gates is empty', () => {
  const { container } = render(<GateBatchCard gates={[]} onDecision={vi.fn()} />)
  expect(container.innerHTML).toBe('')
})

test('shows pending count in header', () => {
  render(<GateBatchCard gates={gates} onDecision={vi.fn()} />)
  expect(screen.getByText(/3 tools need approval/i)).toBeInTheDocument()
})

test('shows singular for 1 tool', () => {
  render(<GateBatchCard gates={[gates[0]]} onDecision={vi.fn()} />)
  expect(screen.getByText(/1 tool needs approval/i)).toBeInTheDocument()
})

test('shows tool names', () => {
  render(<GateBatchCard gates={gates} onDecision={vi.fn()} />)
  expect(screen.getByText('powershell')).toBeInTheDocument()
  expect(screen.getByText('write_file')).toBeInTheDocument()
  expect(screen.getByText('create_file')).toBeInTheDocument()
})

test('approve all calls onDecision for each gate', () => {
  const onDecision = vi.fn()
  render(<GateBatchCard gates={gates} onDecision={onDecision} />)
  fireEvent.click(screen.getByRole('button', { name: /approve all/i }))
  expect(onDecision).toHaveBeenCalledTimes(3)
  expect(onDecision).toHaveBeenCalledWith('g_01', 'allow_once')
  expect(onDecision).toHaveBeenCalledWith('g_02', 'allow_once')
  expect(onDecision).toHaveBeenCalledWith('g_03', 'allow_once')
})

test('deny all calls onDecision deny for each gate', () => {
  const onDecision = vi.fn()
  render(<GateBatchCard gates={gates} onDecision={onDecision} />)
  fireEvent.click(screen.getByRole('button', { name: /deny all/i }))
  expect(onDecision).toHaveBeenCalledTimes(3)
  onDecision.mock.calls.forEach(([gateId, decision]) => {
    expect(decision).toBe('deny')
  })
})

test('individual approve button calls onDecision', () => {
  const onDecision = vi.fn()
  render(<GateBatchCard gates={gates} onDecision={onDecision} />)
  const approveButtons = screen.getAllByTitle('Allow')
  fireEvent.click(approveButtons[0])
  expect(onDecision).toHaveBeenCalledWith('g_01', 'allow_once')
})

test('individual deny button calls onDecision', () => {
  const onDecision = vi.fn()
  render(<GateBatchCard gates={gates} onDecision={onDecision} />)
  const denyButtons = screen.getAllByTitle('Deny')
  fireEvent.click(denyButtons[1])
  expect(onDecision).toHaveBeenCalledWith('g_02', 'deny')
})

test('marks tool as approved after individual approve', () => {
  const onDecision = vi.fn()
  render(<GateBatchCard gates={gates} onDecision={onDecision} />)
  const approveButtons = screen.getAllByTitle('Allow')
  fireEvent.click(approveButtons[0])
  expect(screen.getByText('Approved')).toBeInTheDocument()
})

test('marks tool as denied after individual deny', () => {
  const onDecision = vi.fn()
  render(<GateBatchCard gates={gates} onDecision={onDecision} />)
  const denyButtons = screen.getAllByTitle('Deny')
  fireEvent.click(denyButtons[0])
  expect(screen.getByText('Denied')).toBeInTheDocument()
})
