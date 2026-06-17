'use client'
import React, { useCallback, useState } from 'react'
import { Mic } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

type RecognitionState = 'idle' | 'capturing' | 'permission-denied' | 'error'

interface Props {
  enabled: boolean
  captureOnce: () => Promise<string>
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
  setText: (fn: (prev: string) => string) => void
  onPermissionDenied: () => void
  onError: (code: string) => void
}

export function VoiceButton({ enabled, captureOnce, textareaRef, setText, onPermissionDenied, onError }: Props) {
  const [state, setState] = useState<RecognitionState>('idle')

  const insertAtCursor = useCallback((transcript: string) => {
    setText(prev => {
      const el = textareaRef.current
      if (!el) return prev + transcript
      const before = prev.slice(0, el.selectionStart)
      const after = prev.slice(el.selectionEnd)
      return before + transcript + after
    })
  }, [textareaRef, setText])

  const handleCapture = useCallback(async () => {
    try {
      setState('capturing')
      const transcript = await captureOnce()
      insertAtCursor(transcript)
      setState('idle')
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err)
      if (errMsg.includes('permission') || errMsg.includes('not-allowed')) {
        setState('permission-denied')
        onPermissionDenied()
      } else {
        setState('error')
        onError(errMsg)
      }
      setState('idle')
    }
  }, [captureOnce, insertAtCursor, onPermissionDenied, onError])

  if (!enabled) return null

  const isDisabled = state === 'permission-denied'

  return (
    <Tooltip>
      <TooltipTrigger render={
        <Button
          size="icon"
          className="w-7 h-7"
          aria-label="Voice input"
          disabled={isDisabled || state === 'capturing'}
          onClick={handleCapture}
          variant={state === 'capturing' ? 'default' : 'ghost'}
          data-mic-state={state}
        >
          {state === 'capturing' ? <Mic className="w-4 h-4 animate-pulse" /> : <Mic className="w-4 h-4" />}
        </Button>
      } />
      <TooltipContent>
        {state === 'capturing' ? 'Listening\u2026' : isDisabled ? 'Microphone access blocked' : 'Press to talk'}
      </TooltipContent>
    </Tooltip>
  )
}
