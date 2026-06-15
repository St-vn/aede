'use client'
import React, { useRef, useCallback, useEffect, useState } from 'react'
import { Mic, MicOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SR = typeof window !== 'undefined'
  ? (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
  : undefined

type RecognitionState = 'idle' | 'requesting-permission' | 'listening' | 'permission-denied' | 'error'

interface Props {
  enabled: boolean
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
  setText: (fn: (prev: string) => string) => void
  onPermissionDenied: () => void
  onError: (code: string) => void
}

export function VoiceButton({ enabled, textareaRef, setText, onPermissionDenied, onError }: Props) {
  const [state, setState] = useState<RecognitionState>('idle')
  const recognitionRef = useRef<InstanceType<typeof SR> | null>(null)

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort()
    }
  }, [])

  const insertAtCursor = useCallback((transcript: string) => {
    setText(prev => {
      const el = textareaRef.current
      if (!el) return prev + transcript
      const before = prev.slice(0, el.selectionStart)
      const after = prev.slice(el.selectionEnd)
      return before + transcript + after
    })
  }, [textareaRef, setText])

  const toggle = useCallback(() => {
    if (state === 'listening') {
      recognitionRef.current?.stop()
      setState('idle')
      return
    }
    if (!SR) return
    setState('requesting-permission')
    const recognition = new SR()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = navigator.language

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript
      insertAtCursor(transcript)
      setState('idle')
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (event: any) => {
      const code: string = event.error
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        setState('permission-denied')
        onPermissionDenied()
      } else if (code === 'no-speech' || code === 'aborted') {
        setState('idle')
      } else {
        setState('error')
        onError(code)
      }
    }

    recognition.onend = () => {
      setState(s => s === 'listening' ? 'idle' : s)
    }

    recognition.start()
    recognitionRef.current = recognition
    setState('listening')
  }, [state, insertAtCursor, onPermissionDenied, onError])

  if (!SR || !enabled) return null

  const isDisabled = state === 'permission-denied'

  return (
    <Tooltip>
      <TooltipTrigger render={
        <Button
          size="icon"
          className="w-7 h-7"
          aria-label="Voice input"
          disabled={isDisabled}
          onClick={toggle}
          variant={state === 'listening' ? 'default' : 'ghost'}
          data-mic-state={state}
        >
          {state === 'listening' ? <Mic className="w-4 h-4 animate-pulse" /> : <Mic className="w-4 h-4" />}
        </Button>
      } />
      <TooltipContent>
        {state === 'listening' ? 'Listening\u2026' : isDisabled ? 'Microphone access blocked' : 'Press to talk'}
      </TooltipContent>
    </Tooltip>
  )
}
