'use client'
import React, { useRef, useEffect, useCallback, useState } from 'react'
import { matchWakeWord, type SoulData } from './matchWakeWord'
import { handleRecognitionError } from './ErrorDisplay'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SR = typeof window !== 'undefined'
  ? (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
  : undefined

type WakeWordState = 'disabled' | 'starting' | 'continuous-listening' | 'activated'

interface Props {
  enabled: boolean
  soul: SoulData | null
  sessionId: string | null
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
  setText: (fn: (prev: string) => string) => void
  submit: () => void
}

const FOLLOW_UP_TIMEOUT_MS = 5000
const RESTART_DELAY_MS = 250
const MAX_CONSECUTIVE_FAILURES = 5
const BACKOFF_YIELD_MS = 30000

export function WakeWordListener({ enabled, soul, sessionId, textareaRef, setText, submit }: Props) {
  const [state, setState] = useState<WakeWordState>('disabled')
  const continuousRef = useRef<InstanceType<typeof SR> | null>(null)
  const followUpRef = useRef<InstanceType<typeof SR> | null>(null)
  const failuresRef = useRef(0)
  const disabledRef = useRef(false)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const triggerWakeEvent = useCallback((wakeWord: string, matchedText: string) => {
    if (!sessionId) return
    fetch('/api/voice/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        wake_word: wakeWord,
        matched_text: matchedText,
        source: 'browser',
      }),
    }).catch(() => {})
  }, [sessionId])

  const startFollowUp = useCallback((wakeWord: string) => {
    if (!SR) return
    setState('activated')
    const followUp = new SR()
    followUp.continuous = false
    followUp.interimResults = true
    followUp.lang = navigator.language

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    followUp.onresult = (event: any) => {
      const results = event.results
      for (let i = event.resultIndex; i < results.length; i++) {
        if (results[i].isFinal) {
          const transcript = results[i][0].transcript
          setText(prev => prev + ' ' + transcript)
          // Auto-submit on final result
          submit()
          setState('continuous-listening')
          return
        }
      }
    }

    const resetSilenceTimeout = () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = setTimeout(() => {
        followUp.abort()
        setState('continuous-listening')
      }, FOLLOW_UP_TIMEOUT_MS)
    }

    followUp.onaudiostart = resetSilenceTimeout
    followUp.onaudioend = resetSilenceTimeout
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    followUp.onerror = (event: any) => {
      handleRecognitionError(event.error)
      setState('continuous-listening')
    }

    followUp.start()
    followUpRef.current = followUp
    resetSilenceTimeout()
  }, [setText, submit])

  const startContinuous = useCallback(() => {
    if (!SR || !soul?.wake_word || disabledRef.current) return
    setState('starting')
    const recognition = new SR()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = navigator.language

    const wakeWord = soul.wake_word
    if (wakeWord) {
      try { recognition.phrases = [wakeWord, ...(soul.aliases || [])] } catch {}
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      if (!disabledRef.current) return
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          const transcript = event.results[i][0].transcript
          const matched = matchWakeWord(transcript, soul)
          if (matched) {
            failuresRef.current = 0
            recognition.stop()
            const soulName = soul.name || 'yes'
            setText(() => `${soulName}? `)
            textareaRef.current?.focus()
            triggerWakeEvent(matched, transcript)
            startFollowUp(matched)
            return
          }
        }
      }
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (event: any) => {
      const code: string = event.error
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        handleRecognitionError(code)
        return
      }
      failuresRef.current += 1
      if (failuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        setTimeout(() => { failuresRef.current = 0 }, BACKOFF_YIELD_MS)
      }
    }

    recognition.onend = () => {
      if (!disabledRef.current) return
      setTimeout(() => {
        if (!disabledRef.current) startContinuous()
      }, RESTART_DELAY_MS)
    }

    recognition.start()
    continuousRef.current = recognition
    setState('continuous-listening')
  }, [soul, textareaRef, triggerWakeEvent, startFollowUp])

  useEffect(() => {
    disabledRef.current = !enabled
    if (enabled && soul?.wake_word && SR) {
      startContinuous()
    } else {
      continuousRef.current?.abort()
      followUpRef.current?.abort()
      setState('disabled')
    }
    return () => {
      disabledRef.current = true
      continuousRef.current?.abort()
      followUpRef.current?.abort()
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    }
  }, [enabled, soul?.wake_word, startContinuous])

  return null
}
