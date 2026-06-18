'use client'
import React, { useState } from 'react'
import { MessageCircleQuestion } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface AskUserRequest {
  questionId: string
  question: string
  choices?: string[]
}

interface Props {
  request: AskUserRequest
  onAnswer: (questionId: string, answer: string) => void
}

export function AskUserCard({ request, onAnswer }: Props) {
  const { questionId, question, choices } = request
  const [text, setText] = useState('')

  const handleSubmit = () => {
    const answer = text.trim()
    if (!answer) return
    onAnswer(questionId, answer)
  }

  const handleChoice = (choice: string) => {
    onAnswer(questionId, choice)
  }

  return (
    <div role="status"
      className="border border-border border-l-2 border-l-[--color-info] rounded-lg p-4 my-2 bg-card">
      <div className="flex items-center gap-2 mb-3">
        <MessageCircleQuestion className="w-4 h-4 text-[--color-info] shrink-0" />
        <span className="font-mono text-sm text-foreground">Agent asks</span>
      </div>
      <p className="text-sm text-foreground mb-3">{question}</p>
      {choices && choices.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {choices.map(choice => (
            <Button key={choice} size="sm" variant="outline"
              onClick={() => handleChoice(choice)}>
              {choice}
            </Button>
          ))}
        </div>
      ) : (
        <div className="flex gap-2">
          <Input
            aria-label="Your answer"
            placeholder="Type your answer..."
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          />
          <Button size="sm" onClick={handleSubmit} disabled={!text.trim()}>
            Send
          </Button>
        </div>
      )}
    </div>
  )
}
