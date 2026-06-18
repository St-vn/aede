'use client'
import React, { useState, useCallback } from 'react'
import { MessageCircleQuestion } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'

interface Question {
  header: string
  question: string
  type: 'single' | 'multi' | 'text'
  options?: string[]
  allow_custom?: boolean
  allow_notes?: boolean
  required?: boolean
}

interface Props {
  request: {
    questionId: string
    questions: Question[]
  }
  onAnswer: (questionId: string, answers: Record<string, string | string[] | { value: string | string[]; notes: string }>) => void
}

type AnswerValue = string | string[]

interface AnswersState {
  [question: string]: AnswerValue
}

interface NotesState {
  [question: string]: string
}

export function QuestionCard({ request, onAnswer }: Props) {
  const { questionId, questions } = request
  const [answers, setAnswers] = useState<AnswersState>({})
  const [notes, setNotes] = useState<NotesState>({})
  const [customTexts, setCustomTexts] = useState<Record<string, string>>({})
  const [customSelected, setCustomSelected] = useState<Record<string, boolean>>({})

  const allRequiredAnswered = questions
    .filter(q => q.required !== false)
    .every(q => {
      if (q.type === 'single' && customSelected[q.question]) return (customTexts[q.question]?.trim()?.length ?? 0) > 0
      const ans = answers[q.question]
      if (!ans) return false
      if (q.type === 'text') return (ans as string).trim().length > 0
      if (q.type === 'multi') return (ans as string[]).length > 0
      return true
    })

  const handleSingleChange = useCallback((questionText: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionText]: value }))
  }, [])

  const handleMultiChange = useCallback((questionText: string, option: string, checked: boolean) => {
    setAnswers(prev => {
      const current = (prev[questionText] as string[]) || []
      const next = checked
        ? [...current, option]
        : current.filter(o => o !== option)
      return { ...prev, [questionText]: next }
    })
  }, [])

  const handleTextChange = useCallback((questionText: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionText]: value }))
  }, [])

  const handleCustomTextChange = useCallback((questionText: string, value: string) => {
    setCustomTexts(prev => ({ ...prev, [questionText]: value }))
  }, [])

  const handleCustomSelect = useCallback((questionText: string, selected: boolean) => {
    setCustomSelected(prev => ({ ...prev, [questionText]: selected }))
  }, [])

  const handleNoteChange = useCallback((questionText: string, value: string) => {
    setNotes(prev => ({ ...prev, [questionText]: value }))
  }, [])

  const handleSubmit = useCallback(() => {
    const result: Record<string, string | string[] | { value: string | string[]; notes: string }> = {}
    for (const q of questions) {
      const ans = answers[q.question]
      let value: string | string[] | undefined = ans

      if (q.type === 'single' && customSelected[q.question]) {
        value = customTexts[q.question] || ''
      }

      if (value === undefined || (typeof value === 'string' && !value.trim()) || (Array.isArray(value) && value.length === 0)) {
        continue
      }

      const note = notes[q.question]
      if (q.allow_notes && note && note.trim()) {
        result[q.question] = { value, notes: note.trim() }
      } else {
        result[q.question] = value
      }
    }
    onAnswer(questionId, result)
  }, [questionId, questions, answers, notes, customTexts, customSelected, onAnswer])

  return (
    <div role="status"
      className="border border-border border-l-2 border-l-[--color-info] rounded-lg p-4 my-2 bg-card">
      <div className="flex items-center gap-2 mb-3">
        <MessageCircleQuestion className="w-4 h-4 text-[--color-info] shrink-0" />
        <span className="font-mono text-sm text-foreground">Agent asks</span>
      </div>
      <div className="space-y-4">
        {questions.map((q, qi) => (
          <div key={qi} className="space-y-2">
            <div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{q.header}</span>
              <p className="text-sm text-foreground mt-0.5">{q.question}</p>
            </div>
            {q.type === 'single' && q.options && (
              <RadioGroup>
                {q.options.map(opt => (
                  <RadioGroupItem
                    key={opt}
                    label={opt}
                    name={`question-${qi}`}
                    checked={answers[q.question] === opt}
                    onChange={() => {
                      handleSingleChange(q.question, opt)
                      handleCustomSelect(q.question, false)
                    }}
                  />
                ))}
                {q.allow_custom && (
                  <div className="flex flex-col gap-1">
                    <RadioGroupItem
                      label="Other…"
                      name={`question-${qi}`}
                      checked={!!customSelected[q.question]}
                      onChange={() => {
                        handleCustomSelect(q.question, true)
                        handleSingleChange(q.question, '')
                      }}
                    />
                    {customSelected[q.question] && (
                      <Input
                        aria-label="Custom answer"
                        placeholder="Type custom answer…"
                        value={customTexts[q.question] || ''}
                        onChange={e => handleCustomTextChange(q.question, e.target.value)}
                        className="ml-6"
                      />
                    )}
                  </div>
                )}
              </RadioGroup>
            )}
            {q.type === 'multi' && q.options && (
              <div className="space-y-1">
                {q.options.map(opt => {
                  const selected = (answers[q.question] as string[]) || []
                  return (
                    <Checkbox
                      key={opt}
                      label={opt}
                      checked={selected.includes(opt)}
                      onChange={e => handleMultiChange(q.question, opt, (e.target as HTMLInputElement).checked)}
                    />
                  )
                })}
              </div>
            )}
            {q.type === 'text' && (
              <Textarea
                aria-label={q.question}
                placeholder="Type your answer…"
                value={(answers[q.question] as string) || ''}
                onChange={e => handleTextChange(q.question, e.target.value)}
              />
            )}
            {q.allow_notes && (
              <Textarea
                aria-label={`Note for: ${q.question}`}
                placeholder="Add note…"
                value={notes[q.question] || ''}
                onChange={e => handleNoteChange(q.question, e.target.value)}
                className="text-xs min-h-[60px]"
              />
            )}
          </div>
        ))}
      </div>
      <div className="mt-4">
        <Button size="sm" onClick={handleSubmit} disabled={!allRequiredAnswered}>
          Submit
        </Button>
      </div>
    </div>
  )
}
