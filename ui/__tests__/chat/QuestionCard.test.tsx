import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QuestionCard } from '../../components/chat/QuestionCard'

function makeRequest(overrides?: Record<string, unknown>) {
  return {
    request: {
      questionId: 'q1',
      questions: [
        {
          header: 'Format',
          question: 'How should I format the output?',
          type: 'single',
          options: ['Summary', 'Detailed'],
          allow_custom: false,
          allow_notes: false,
          required: true,
        },
      ],
      ...overrides,
    },
    onAnswer: vi.fn(),
  }
}

test('renders single-select radio buttons', () => {
  const props = makeRequest()
  render(<QuestionCard {...props} />)
  expect(screen.getByRole('radio', { name: 'Summary' })).toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'Detailed' })).toBeInTheDocument()
})

test('renders multi-select checkboxes', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Sections',
        question: 'Which sections?',
        type: 'multi' as const,
        options: ['Intro', 'Body', 'Conclusion'],
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  expect(screen.getByRole('checkbox', { name: 'Intro' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Body' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Conclusion' })).toBeInTheDocument()
})

test('renders text textarea', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Notes',
        question: 'Any additional context?',
        type: 'text' as const,
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const textarea = screen.getByRole('textbox')
  expect(textarea).toBeInTheDocument()
  fireEvent.change(textarea, { target: { value: 'Keep it short' } })
  expect(textarea).toHaveValue('Keep it short')
})

test('custom "Other…" reveals text input for single-select', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: true,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  expect(screen.getByRole('radio', { name: 'Summary' })).toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'Detailed' })).toBeInTheDocument()
  expect(screen.getByRole('radio', { name: /other/i })).toBeInTheDocument()
})

test('custom "Other…" reveals text input when selected for single-select', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: true,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const otherRadio = screen.getByRole('radio', { name: /other/i })
  fireEvent.click(otherRadio)
  const customInput = screen.getByPlaceholderText(/custom/i)
  expect(customInput).toBeInTheDocument()
  fireEvent.change(customInput, { target: { value: 'Custom answer' } })
  expect(customInput).toHaveValue('Custom answer')
})

test('notes textarea shown when allow_notes is true', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: false,
        allow_notes: true,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const noteTextareas = screen.getAllByPlaceholderText(/add note/i)
  expect(noteTextareas.length).toBeGreaterThanOrEqual(1)
})

test('submit disabled until all required questions answered', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
      {
        header: 'Sections',
        question: 'Which sections?',
        type: 'multi' as const,
        options: ['Intro', 'Body'],
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const submitButton = screen.getByRole('button', { name: /submit/i })
  expect(submitButton).toBeDisabled()
})

test('submit button enabled when all required answered', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const submitButton = screen.getByRole('button', { name: /submit/i })
  expect(submitButton).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  expect(submitButton).toBeEnabled()
})

test('non-required questions do not block submit', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Optional',
        question: 'Any extra?',
        type: 'text' as const,
        allow_custom: false,
        allow_notes: false,
        required: false,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const submitButton = screen.getByRole('button', { name: /submit/i })
  expect(submitButton).toBeEnabled()
})

test('submits single-select answer', () => {
  const props = makeRequest()
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'How should I format the output?': 'Summary',
  })
})

test('submits multi-select answer as array', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Sections',
        question: 'Which sections?',
        type: 'multi' as const,
        options: ['Intro', 'Body', 'Conclusion'],
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('checkbox', { name: 'Intro' }))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Conclusion' }))
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'Which sections?': ['Intro', 'Conclusion'],
  })
})

test('submits text answer', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Notes',
        question: 'Any context?',
        type: 'text' as const,
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const textarea = screen.getByRole('textbox')
  fireEvent.change(textarea, { target: { value: 'Keep it short' } })
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'Any context?': 'Keep it short',
  })
})

test('submits custom answer instead of "Other"', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: true,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: /other/i }))
  const customInput = screen.getByPlaceholderText(/custom/i)
  fireEvent.change(customInput, { target: { value: 'Bullet points' } })
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'How should I format the output?': 'Bullet points',
  })
})

test('notes included in submitted answer', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: false,
        allow_notes: true,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  const noteTextareas = screen.getAllByPlaceholderText(/add note/i)
  fireEvent.change(noteTextareas[0], { target: { value: 'Because it is concise' } })
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'How should I format the output?': {
      value: 'Summary',
      notes: 'Because it is concise',
    },
  })
})

test('empty notes omitted from answer', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        allow_custom: false,
        allow_notes: true,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  fireEvent.click(screen.getByRole('button', { name: /submit/i }))
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'How should I format the output?': 'Summary',
  })
})

test('renders AGENT ASKS label', () => {
  const props = makeRequest()
  render(<QuestionCard {...props} />)
  expect(screen.getByText(/agent asks/i)).toBeInTheDocument()
})
