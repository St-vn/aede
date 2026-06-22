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

test('success card is expandable', async () => {
  render(<ToolCallCard toolName="read_file" status="success" args={{ path: '/tmp/x' }} output="content" durationMs={10} />)
  // Header now has a label toggle and a chevron toggle; either expands it.
  const expand = screen.getByRole('button', { name: /expand/i })
  fireEvent.click(expand)
  expect(screen.getByText('content')).toBeInTheDocument()
})

test('question tool renders Q and A on separate lines', async () => {
  render(
    <ToolCallCard
      toolName="question"
      status="success"
      args={{}}
      output={JSON.stringify({ answers: { 'What is your name?': 'Alice' } })}
      durationMs={10}
    />
  )
  const expand = screen.getByRole('button', { name: /expand/i })
  fireEvent.click(expand)
  expect(screen.getByText(/Q: What is your name?/)).toBeInTheDocument()
  expect(screen.getByText(/A: Alice/)).toBeInTheDocument()
})

test('question tool renders multi-select options each on their own line', async () => {
  render(
    <ToolCallCard
      toolName="ask_user_choices"
      status="success"
      args={{}}
      output={JSON.stringify({ answers: { 'Pick one': ['A', 'B'] } })}
      durationMs={10}
    />
  )
  const expand = screen.getByRole('button', { name: /expand/i })
  fireEvent.click(expand)
  expect(screen.getByText(/Q: Pick one/)).toBeInTheDocument()
  expect(screen.getByText(/A: A/)).toBeInTheDocument()
  expect(screen.getByText(/B/)).toBeInTheDocument()
})

test('question tool renders notes when answer is an object', async () => {
  render(
    <ToolCallCard
      toolName="question"
      status="success"
      args={{}}
      output={JSON.stringify({ answers: { 'Why?': { value: 'Because', notes: 'More context' } } })}
      durationMs={10}
    />
  )
  const expand = screen.getByRole('button', { name: /expand/i })
  fireEvent.click(expand)
  expect(screen.getByText(/Q: Why?/)).toBeInTheDocument()
  expect(screen.getByText(/A: Because/)).toBeInTheDocument()
  expect(screen.getByText(/Note: More context/)).toBeInTheDocument()
})
