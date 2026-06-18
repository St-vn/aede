import React from 'react'
import { vi, test, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AskUserCard } from '../../components/chat/AskUserCard'

function makeProps(overrides?: { questionId?: string; question?: string; choices?: string[] }) {
  return {
    request: {
      questionId: overrides?.questionId ?? 'q1',
      question: overrides?.question ?? 'What is your name?',
      choices: overrides?.choices,
    },
    onAnswer: vi.fn(),
  }
}

test('renders question text', () => {
  const props = makeProps()
  render(<AskUserCard {...props} />)
  expect(screen.getByText('What is your name?')).toBeInTheDocument()
})

test('renders AGENT ASKS label', () => {
  const props = makeProps()
  render(<AskUserCard {...props} />)
  expect(screen.getByText(/agent asks/i)).toBeInTheDocument()
})

test('text input submits answer on Enter', () => {
  const props = makeProps()
  render(<AskUserCard {...props} />)
  const input = screen.getByRole('textbox', { name: /your answer/i })
  fireEvent.change(input, { target: { value: 'Alice' } })
  fireEvent.keyDown(input, { key: 'Enter' })
  expect(props.onAnswer).toHaveBeenCalledWith('q1', 'Alice')
})

test('text input submits answer on button click', () => {
  const props = makeProps()
  render(<AskUserCard {...props} />)
  const input = screen.getByRole('textbox', { name: /your answer/i })
  fireEvent.change(input, { target: { value: 'Bob' } })
  fireEvent.click(screen.getByRole('button', { name: /send/i }))
  expect(props.onAnswer).toHaveBeenCalledWith('q1', 'Bob')
})

test('empty answer does not submit', () => {
  const props = makeProps()
  render(<AskUserCard {...props} />)
  fireEvent.click(screen.getByRole('button', { name: /send/i }))
  expect(props.onAnswer).not.toHaveBeenCalled()
})

test('renders choice buttons when choices provided', () => {
  const props = makeProps({ choices: ['Yes', 'No', 'Maybe'] })
  render(<AskUserCard {...props} />)
  expect(screen.getByRole('button', { name: 'Yes' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'No' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Maybe' })).toBeInTheDocument()
})

test('clicking choice calls onAnswer', () => {
  const props = makeProps({ questionId: 'q2', choices: ['A', 'B'] })
  render(<AskUserCard {...props} />)
  fireEvent.click(screen.getByRole('button', { name: 'B' }))
  expect(props.onAnswer).toHaveBeenCalledWith('q2', 'B')
})

test('no text input when choices provided', () => {
  const props = makeProps({ choices: ['X'] })
  render(<AskUserCard {...props} />)
  expect(screen.queryByRole('textbox', { name: /your answer/i })).not.toBeInTheDocument()
})
