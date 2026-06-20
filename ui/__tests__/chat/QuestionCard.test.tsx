import React from 'react'
import { vi, test, expect } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
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

test('Continue enabled after typing in text question', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Quiz Q1',
        question: 'Your email contains chhun in it?',
        type: 'text' as const,
        allow_custom: false,
        allow_notes: false,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const saveButton = screen.getByTestId('save-question-0')
  expect(saveButton).toBeDisabled()
  const textarea = screen.getByRole('textbox')
  fireEvent.change(textarea, { target: { value: 'yes' } })
  expect(saveButton).toBeEnabled()
})

test('custom "Give your own answer" reveals text input for single-select', () => {
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
  expect(screen.getByRole('radio', { name: /give your own answer/i })).toBeInTheDocument()
})

test('custom "Give your own answer" reveals text input when selected for single-select', () => {
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
  const customRadio = screen.getByRole('radio', { name: /give your own answer/i })
  fireEvent.click(customRadio)
  const customInput = screen.getByPlaceholderText(/your own answer/i)
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

test('Save & continue disabled until current required question answered', () => {
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
  const saveButton = screen.getByTestId('save-question-0')
  expect(saveButton).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  expect(saveButton).toBeEnabled()
})

test('Review Submit all answers disabled until all required answered', () => {
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
  fireEvent.click(screen.getByTestId('review-tab'))
  expect(screen.getByTestId('submit-all-answers')).toBeDisabled()
})

test('non-required questions do not block Save & continue', () => {
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
  expect(screen.getByTestId('save-question-0')).toBeEnabled()
})

function submitSingleAnswer(cardProps: ReturnType<typeof makeRequest>) {
  fireEvent.click(screen.getByTestId('save-question-0'))
  fireEvent.click(screen.getByTestId('submit-all-answers'))
}

test('submits single-select answer', () => {
  const props = makeRequest()
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  submitSingleAnswer(props)
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
  submitSingleAnswer(props)
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
  submitSingleAnswer(props)
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'Any context?': 'Keep it short',
  })
})

test('submits custom answer instead of preset option', () => {
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
  fireEvent.click(screen.getByRole('radio', { name: /give your own answer/i }))
  const customInput = screen.getByPlaceholderText(/your own answer/i)
  fireEvent.change(customInput, { target: { value: 'Bullet points' } })
  submitSingleAnswer(props)
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
  submitSingleAnswer(props)
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
  submitSingleAnswer(props)
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'How should I format the output?': 'Summary',
  })
})

test('renders AGENT ASKS label', () => {
  const props = makeRequest()
  render(<QuestionCard {...props} />)
  expect(screen.getByText(/agent asks/i)).toBeInTheDocument()
})

test('renders one tab per question plus a Review tab', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'First',
        question: 'Q1?',
        type: 'single' as const,
        options: ['A', 'B'],
        required: true,
      },
      {
        header: 'Second',
        question: 'Q2?',
        type: 'text' as const,
        required: true,
      },
      {
        header: 'Third',
        question: 'Q3?',
        type: 'text' as const,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  expect(screen.getByTestId('question-tab-0')).toBeInTheDocument()
  expect(screen.getByTestId('question-tab-1')).toBeInTheDocument()
  expect(screen.getByTestId('question-tab-2')).toBeInTheDocument()
  expect(screen.getByTestId('review-tab')).toBeInTheDocument()
})

test('clicking a question tab shows that question content', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        required: true,
      },
      {
        header: 'Notes',
        question: 'Any additional context?',
        type: 'text' as const,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  expect(screen.getByRole('radio', { name: 'Summary' })).toBeInTheDocument()
  fireEvent.click(screen.getByTestId('question-tab-1'))
  expect(screen.getByRole('textbox')).toBeInTheDocument()
})

test('Review tab shows all answers in Q: X; A: Y format', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        required: true,
      },
      {
        header: 'Sections',
        question: 'Which sections?',
        type: 'multi' as const,
        options: ['Intro', 'Body', 'Conclusion'],
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  fireEvent.click(screen.getByTestId('question-tab-1'))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Intro' }))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Conclusion' }))
  fireEvent.click(screen.getByTestId('review-tab'))
  expect(screen.getByTestId('review-q-0')).toHaveTextContent('Q: How should I format the output?')
  expect(screen.getByTestId('review-a-0')).toHaveTextContent('A: Summary')
  expect(screen.getByTestId('review-q-1')).toHaveTextContent('Q: Which sections?')
  expect(screen.getByTestId('review-a-1')).toHaveTextContent('A: Intro, Conclusion')
})

test('Review tab shows unanswered questions with A: —', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByTestId('review-tab'))
  expect(screen.getByTestId('review-a-0')).toHaveTextContent('A: —')
})

test('Save & continue advances to Review tab for single question', () => {
  const props = makeRequest()
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  fireEvent.click(screen.getByTestId('save-question-0'))
  expect(screen.getByTestId('submit-all-answers')).toBeInTheDocument()
})

test('Save & continue advances to next question when multiple exist', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'First',
        question: 'Q1?',
        type: 'single' as const,
        options: ['A', 'B'],
        required: true,
      },
      {
        header: 'Second',
        question: 'Q2?',
        type: 'text' as const,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'A' }))
  fireEvent.click(screen.getByTestId('save-question-0'))
  expect(screen.getByText('Q2?')).toBeInTheDocument()
})

test('Chat about this sends chat via onChat and does not submit an answer', () => {
  const onChat = vi.fn()
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} onChat={onChat} />)
  fireEvent.click(screen.getByTestId('chat-toggle-0'))
  const chatTextarea = screen.getByPlaceholderText(/would you like to discuss/i)
  fireEvent.change(chatTextarea, { target: { value: 'I want to discuss alternatives' } })
  fireEvent.click(screen.getByTestId('send-chat-0'))
  expect(onChat).toHaveBeenCalledWith('q1', 'How should I format the output?', 'I want to discuss alternatives')
  expect(props.onAnswer).not.toHaveBeenCalled()
})

test('multi-select supports Give your own answer', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Sections',
        question: 'Which sections?',
        type: 'multi' as const,
        options: ['Intro', 'Body'],
        allow_custom: true,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('checkbox', { name: /give your own answer/i }))
  const customInput = screen.getByPlaceholderText(/your own answer/i)
  fireEvent.change(customInput, { target: { value: 'Appendix' } })
  submitSingleAnswer(props)
  expect(props.onAnswer).toHaveBeenCalledWith('q1', {
    'Which sections?': ['Appendix'],
  })
})

test('Review tab shows check icon for answered and circle for unanswered', () => {
  const props = makeRequest({
    questions: [
      {
        header: 'Format',
        question: 'How should I format the output?',
        type: 'single' as const,
        options: ['Summary', 'Detailed'],
        required: true,
      },
      {
        header: 'Notes',
        question: 'Any additional context?',
        type: 'text' as const,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Summary' }))
  fireEvent.click(screen.getByTestId('review-tab'))
  expect(screen.getByTestId('review-check-0')).toBeInTheDocument()
  expect(screen.getByTestId('review-circle-1')).toBeInTheDocument()
})

test('tabs are keyboard navigable', async () => {
  const props = makeRequest({
    questions: [
      {
        header: 'First',
        question: 'Q1?',
        type: 'single' as const,
        options: ['A'],
        required: true,
      },
      {
        header: 'Second',
        question: 'Q2?',
        type: 'text' as const,
        required: true,
      },
      {
        header: 'Third',
        question: 'Q3?',
        type: 'text' as const,
        required: true,
      },
    ],
  })
  render(<QuestionCard {...props} />)
  const firstTab = screen.getByTestId('question-tab-0')
  const secondTab = screen.getByTestId('question-tab-1')
  firstTab.focus()
  expect(firstTab).toHaveFocus()
  await act(async () => {
    fireEvent.keyDown(firstTab, { key: 'ArrowRight' })
    await Promise.resolve()
  })
  expect(secondTab).toHaveFocus()
})
