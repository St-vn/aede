import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AcpConnectChip } from '../../components/input/AcpConnectChip'

const mockStatus = vi.fn()
const mockConnect = vi.fn()
const mockDisconnect = vi.fn()

vi.mock('@/hooks/useAcpAgents', () => ({
  useStatus: () => mockStatus(),
  useConnect: () => mockConnect(),
  useDisconnect: () => mockDisconnect(),
}))

beforeEach(() => {
  mockStatus.mockReturnValue({ data: { connected: false, active: null, sessions: [] } })
  mockConnect.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null })
  mockDisconnect.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false })
})

test('renders nothing for a non-ACP model', () => {
  const { container } = render(<AcpConnectChip model="claude-sonnet-4" />)
  expect(container.firstChild).toBeNull()
})

test('auto-connects when model is an ACP agent and not connected', () => {
  const connectMutate = vi.fn()
  mockConnect.mockReturnValue({ mutate: connectMutate, isPending: false, isError: false, error: null })
  render(<AcpConnectChip model="claude-code" />)
  expect(connectMutate).toHaveBeenCalledWith('claude-code')
})

test('auto-connects with base agent from sub-model id', () => {
  const connectMutate = vi.fn()
  mockConnect.mockReturnValue({ mutate: connectMutate, isPending: false, isError: false, error: null })
  render(<AcpConnectChip model="claude-code/opus-4-8" />)
  expect(connectMutate).toHaveBeenCalledWith('claude-code')
})

test('does not auto-connect when already connected', () => {
  const connectMutate = vi.fn()
  mockStatus.mockReturnValue({ data: { connected: true, active: 'claude-code', sessions: ['claude-code'] } })
  mockConnect.mockReturnValue({ mutate: connectMutate, isPending: false, isError: false, error: null })
  render(<AcpConnectChip model="claude-code" />)
  expect(connectMutate).not.toHaveBeenCalled()
})

test('renders Connected state when agent is in sessions', () => {
  mockStatus.mockReturnValue({ data: { connected: true, active: 'claude-code', sessions: ['claude-code'] } })
  render(<AcpConnectChip model="claude-code" />)
  expect(screen.getByText('Connected')).toBeInTheDocument()
})

test('disconnect button calls disconnect mutation', () => {
  const disconnectMutate = vi.fn()
  mockStatus.mockReturnValue({ data: { connected: true, active: 'claude-code', sessions: ['claude-code'] } })
  mockDisconnect.mockReturnValue({ mutate: disconnectMutate, isPending: false, isError: false })
  render(<AcpConnectChip model="claude-code" />)
  fireEvent.click(screen.getByRole('button'))
  expect(disconnectMutate).toHaveBeenCalledWith('claude-code')
})

test('shows pending state while connecting', () => {
  mockConnect.mockReturnValue({ mutate: vi.fn(), isPending: true, isError: false, error: null })
  render(<AcpConnectChip model="claude-code" />)
  expect(screen.getByText('Connecting')).toBeInTheDocument()
})

test('shows failed state with error message', () => {
  mockConnect.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: true, error: new Error('agent not installed') })
  render(<AcpConnectChip model="claude-code" />)
  expect(screen.getByText('Failed')).toBeInTheDocument()
  expect(screen.getByTitle('agent not installed')).toBeInTheDocument()
})

test('clicking Failed chip retries connection', () => {
  const connectMutate = vi.fn()
  mockConnect.mockReturnValue({ mutate: connectMutate, isPending: false, isError: true, error: new Error('agent not installed') })
  render(<AcpConnectChip model="claude-code" />)
  fireEvent.click(screen.getByText('Failed'))
  expect(connectMutate).toHaveBeenCalledWith('claude-code')
})
