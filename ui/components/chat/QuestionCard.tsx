'use client'
import React, { useState, useCallback } from 'react'
import { MessageCircleQuestion, Check, Circle, ListChecks } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

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
  onChat?: (questionId: string, questionText: string, comment: string) => void
}

type AnswerValue = string | string[]

interface AnswersState {
  [question: string]: AnswerValue
}

interface NotesState {
  [question: string]: string
}

const REVIEW_TAB = '__review__'

function isQuestionAnswered(
  q: Question,
  answers: AnswersState,
  customTexts: Record<string, string>,
  customSelected: Record<string, boolean>,
  chatMode: Record<string, boolean> = {},
): boolean {
  if (chatMode[q.question]) return true
  if (q.type === 'single') {
    if (customSelected[q.question]) {
      return (customTexts[q.question]?.trim()?.length ?? 0) > 0
    }
    return typeof answers[q.question] === 'string' && (answers[q.question] as string).length > 0
  }
  if (q.type === 'multi') {
    const selected = (answers[q.question] as string[]) || []
    if (selected.length > 0) return true
    return customSelected[q.question] && (customTexts[q.question]?.trim()?.length ?? 0) > 0
  }
  if (q.type === 'text') {
    return typeof answers[q.question] === 'string' && (answers[q.question] as string).trim().length > 0
  }
  return false
}

function formatAnswerForReview(
  q: Question,
  answers: AnswersState,
  customTexts: Record<string, string>,
): string {
  if (q.type === 'single' && answers[q.question] === undefined) {
    return customTexts[q.question] ?? ''
  }
  const ans = answers[q.question]
  if (ans === undefined) return ''
  if (Array.isArray(ans)) return ans.join(', ')
  return ans
}

export function QuestionCard({ request, onAnswer, onChat }: Props) {
  const { questionId, questions } = request
  const [activeTab, setActiveTab] = useState<string>(
    questions[0] ? `q-0` : REVIEW_TAB,
  )
  const [answers, setAnswers] = useState<AnswersState>({})
  const [notes, setNotes] = useState<NotesState>({})
  const [customTexts, setCustomTexts] = useState<Record<string, string>>({})
  const [customSelected, setCustomSelected] = useState<Record<string, boolean>>({})
  const [chatMode, setChatMode] = useState<Record<string, boolean>>({})
  const [chatComments, setChatComments] = useState<Record<string, string>>({})

  const allRequiredAnswered = questions
    .filter(q => q.required !== false)
    .every(q => isQuestionAnswered(q, answers, customTexts, customSelected, chatMode))

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

  const handleChatToggle = useCallback((questionText: string, active: boolean) => {
    setChatMode(prev => ({ ...prev, [questionText]: active }))
  }, [])

  const handleChatCommentChange = useCallback((questionText: string, value: string) => {
    setChatComments(prev => ({ ...prev, [questionText]: value }))
  }, [])

  const handleSubmitAll = useCallback(() => {
    const result: Record<string, string | string[] | { value: string | string[]; notes: string }> = {}
    for (const q of questions) {
      if (chatMode[q.question]) {
        // Chat-mode questions are not submitted as answers; they are sent
        // separately via onChat while the question stays pending.
        continue
      }

      const ans = answers[q.question]
      let value: string | string[] | undefined = ans

      if (q.type === 'single' && customSelected[q.question]) {
        value = customTexts[q.question] || ''
      }

      if (q.type === 'multi' && customSelected[q.question] && customTexts[q.question]?.trim()) {
        value = [...((ans as string[]) || []), customTexts[q.question].trim()]
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
  }, [questionId, questions, answers, notes, customTexts, customSelected, chatMode, onAnswer])

  const handleSaveQuestion = useCallback((qi: number) => {
    const q = questions[qi]
    if (!q) return
    if (q.required !== false && !isQuestionAnswered(q, answers, customTexts, customSelected, chatMode)) {
      return
    }
    const next = questions[qi + 1] ? `q-${qi + 1}` : REVIEW_TAB
    setActiveTab(next)
  }, [questions, answers, customTexts, customSelected, chatMode])

  return (
    <div role="status"
      className="border border-border border-l-2 border-l-[--color-info] rounded-lg p-4 my-2 bg-card">
      <div className="flex items-center gap-2 mb-3">
        <MessageCircleQuestion className="w-4 h-4 text-[--color-info] shrink-0" />
        <span className="font-mono text-sm text-foreground">Agent asks</span>
      </div>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex h-auto w-full justify-start gap-1 overflow-x-auto p-1 mb-3 bg-muted rounded-lg">
          {questions.map((q, qi) => {
            const answered = isQuestionAnswered(q, answers, customTexts, customSelected, chatMode)
            const Icon = answered ? Check : Circle
            return (
              <TabsTrigger
                  key={`${request.questionId}-review-${qi}`}
                value={`q-${qi}`}
                data-answered={answered ? 'true' : 'false'}
                data-testid={`question-tab-${qi}`}
                className="flex items-center gap-1.5 px-2 py-1 text-xs whitespace-nowrap"
              >
                <Icon
                  className={`w-3.5 h-3.5 shrink-0 ${answered ? 'text-green-600' : 'text-muted-foreground'}`}
                  data-testid={answered ? `tab-check-${qi}` : `tab-circle-${qi}`}
                />
                <span>{q.header}</span>
              </TabsTrigger>
            )
          })}
          <TabsTrigger
            value={REVIEW_TAB}
            data-testid="review-tab"
            className="flex items-center gap-1.5 px-2 py-1 text-xs whitespace-nowrap ml-auto"
          >
            <ListChecks className="w-3.5 h-3.5 shrink-0" data-testid="review-icon" />
            <span>Review</span>
          </TabsTrigger>
        </TabsList>
        {questions.map((q, qi) => {
          const isChat = !!chatMode[q.question]
          const currentAnswered = isQuestionAnswered(q, answers, customTexts, customSelected, chatMode)
          return (
            <TabsContent key={`${request.questionId}-panel-${qi}`} value={`q-${qi}`} className="mt-0 space-y-2">
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{q.header}</span>
                <p className="text-sm text-foreground mt-0.5">{q.question}</p>
              </div>
              {!isChat && q.type === 'single' && q.options && (
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
                        label="Give your own answer"
                        name={`question-${qi}`}
                        checked={!!customSelected[q.question]}
                        onChange={() => {
                          handleCustomSelect(q.question, true)
                          handleSingleChange(q.question, '')
                        }}
                      />
                      {customSelected[q.question] && (
                        <Input
                          aria-label="Give your own answer"
                          placeholder="Type your own answer…"
                          value={customTexts[q.question] || ''}
                          onChange={e => handleCustomTextChange(q.question, e.target.value)}
                          className="ml-6"
                        />
                      )}
                    </div>
                  )}
                </RadioGroup>
              )}
              {!isChat && q.type === 'multi' && q.options && (
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
                  {q.allow_custom && (
                    <div className="flex flex-col gap-1">
                      <Checkbox
                        label="Give your own answer"
                        checked={!!customSelected[q.question]}
                        onChange={e => {
                          const checked = (e.target as HTMLInputElement).checked
                          handleCustomSelect(q.question, checked)
                          if (!checked) {
                            handleCustomTextChange(q.question, '')
                          }
                        }}
                      />
                      {customSelected[q.question] && (
                        <Input
                          aria-label="Give your own answer"
                          placeholder="Type your own answer…"
                          value={customTexts[q.question] || ''}
                          onChange={e => handleCustomTextChange(q.question, e.target.value)}
                          className="ml-6"
                        />
                      )}
                    </div>
                  )}
                </div>
              )}
              {!isChat && q.type === 'text' && (
                <Textarea
                  aria-label={q.question}
                  placeholder="Type your answer…"
                  value={(answers[q.question] as string) || ''}
                  onChange={e => handleTextChange(q.question, e.target.value)}
                />
              )}
              {isChat && (
                <Textarea
                  aria-label={`Chat about: ${q.question}`}
                  placeholder="What would you like to discuss or clarify?"
                  value={chatComments[q.question] || ''}
                  onChange={e => handleChatCommentChange(q.question, e.target.value)}
                  data-testid={`chat-input-${qi}`}
                />
              )}
              {q.allow_notes && !isChat && (
                <Textarea
                  aria-label={`Note for: ${q.question}`}
                  placeholder="Add note…"
                  value={notes[q.question] || ''}
                  onChange={e => handleNoteChange(q.question, e.target.value)}
                  className="text-xs min-h-[60px]"
                />
              )}
              <div className="flex items-center justify-between pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs h-7 px-2"
                  onClick={() => handleChatToggle(q.question, !isChat)}
                  data-testid={`chat-toggle-${qi}`}
                >
                  {isChat ? 'Answer instead' : 'Chat about this'}
                </Button>
                {isChat ? (
                  <Button
                    size="sm"
                    onClick={() => {
                      const comment = chatComments[q.question]?.trim() || ''
                      if (comment && onChat) {
                        onChat(questionId, q.question, comment)
                        handleChatCommentChange(q.question, '')
                      }
                    }}
                    disabled={!chatComments[q.question]?.trim() || !onChat}
                    data-testid={`send-chat-${qi}`}
                  >
                    Send chat
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => handleSaveQuestion(qi)}
                    disabled={q.required !== false && !currentAnswered}
                    data-testid={`save-question-${qi}`}
                  >
                    Continue
                  </Button>
                )}
              </div>
            </TabsContent>
          )
        })}
        <TabsContent value={REVIEW_TAB} className="mt-0">
          <div className="space-y-2" data-testid="review-content">
            {questions.map((q, qi) => {
              const answered = isQuestionAnswered(q, answers, customTexts, customSelected, chatMode)
              const answerText = chatMode[q.question]
                ? chatComments[q.question]?.trim() || 'Chat about this'
                : formatAnswerForReview(q, answers, customTexts)
              const note = notes[q.question]
              const Icon = answered ? Check : Circle
              return (
                <div
                key={`${request.questionId}-tab-${qi}`}
                  className="flex items-start gap-2 py-1.5 border-b border-border/40 last:border-b-0"
                  data-testid={`review-row-${qi}`}
                >
                  <Icon
                    className={`w-4 h-4 mt-0.5 shrink-0 ${answered ? 'text-green-600' : 'text-muted-foreground'}`}
                    data-testid={answered ? `review-check-${qi}` : `review-circle-${qi}`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-foreground" data-testid={`review-q-${qi}`}>
                      Q: {q.question}
                    </div>
                    <div
                      className={`text-sm ${answered ? 'text-foreground' : 'text-muted-foreground italic'}`}
                      data-testid={`review-a-${qi}`}
                    >
                      A: {answered ? answerText : '—'}
                    </div>
                    {note && note.trim() && !chatMode[q.question] && (
                      <div className="text-xs text-muted-foreground mt-0.5" data-testid={`review-note-${qi}`}>
                        Note: {note.trim()}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-4 flex justify-end">
            <Button
              size="sm"
              onClick={handleSubmitAll}
              disabled={!allRequiredAnswered}
              data-testid="submit-all-answers"
            >
              Submit all answers
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
