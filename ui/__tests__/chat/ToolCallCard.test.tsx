import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToolCallCard } from '../../components/chat/ToolCallCard'

test('running state shows tool name', () => {
  render(<ToolCallCard toolName="read_file" status="running" args={{}} />)
  expect(screen.getByText('read_file')).toBeInTheDocument()
})

test('running state shows loader indicator text', () => {
  render(<ToolCallCard toolName="read_file" status="running" args={{}} />)
  expect(screen.getByText(/running/i)).toBeInTheDocument()
})

test('success state shows duration', () => {
  render(<ToolCallCard toolName="read_file" status="success" args={{}} durationMs={42} />)
  expect(screen.getByText(/42ms/)).toBeInTheDocument()
})

test('error state communicates error without color alone', () => {
  render(<ToolCallCard toolName="powershell" status="error" args={{}} output="ENOENT" />)
  expect(screen.getByText(/error/i)).toBeInTheDocument()
})

test('denied state shows denied label', () => {
  render(<ToolCallCard toolName="rm" status="denied" args={{}} />)
  expect(screen.getByText(/denied/i)).toBeInTheDocument()
})

test('success card is expandable (Collapsible)', async () => {
  render(<ToolCallCard toolName="read_file" status="success" args={{ path: '/tmp/x' }} output="content" durationMs={10} />)
  const trigger = screen.getByRole('button')
  fireEvent.click(trigger)
  expect(screen.getByText('content')).toBeInTheDocument()
})
