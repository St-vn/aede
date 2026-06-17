'use client'
import React, { useRef, useEffect, useCallback, useState } from 'react'
import { matchWakeWord, type SoulData } from './matchWakeWord'
import { handleRecognitionError } from './ErrorDisplay'
import { apiFetch } from '@/lib/api'

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
  submit: (override?: string) => void
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
  const startingRef = useRef(false)
  const followUpActiveRef = useRef(false)
  const startContinuousRef = useRef<() => void>(() => {})

  const triggerWakeEvent = useCallback((wakeWord: string, matchedText: string) => {
    if (!sessionId) return
    apiFetch('/api/voice/trigger', {
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
    console.debug('[WakeWord] startFollowUp called for:', wakeWord)
    followUpActiveRef.current = true
    setState('activated')
    const followUp = new SR()
    followUp.continuous = false
    followUp.interimResults = true
    followUp.lang = navigator.language

    followUp.onstart = () => console.debug('[WakeWord] followUp recognition started')

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    followUp.onresult = (event: any) => {
      const results = event.results
      for (let i = event.resultIndex; i < results.length; i++) {
        console.debug('[WakeWord] followUp result isFinal:', results[i].isFinal, 'transcript:', results[i][0].transcript)
        if (results[i].isFinal) {
          const transcript = results[i][0].transcript
          followUpActiveRef.current = false
          if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
          submit(transcript)
          setState('continuous-listening')
          setTimeout(() => { if (!disabledRef.current) startContinuousRef.current() }, RESTART_DELAY_MS)
          return
        }
      }
    }

    const resetSilenceTimeout = () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = setTimeout(() => {
        console.debug('[WakeWord] followUp silence timeout — aborting')
        followUpActiveRef.current = false
        followUp.abort()
        setState('continuous-listening')
        setTimeout(() => { if (!disabledRef.current) startContinuousRef.current() }, RESTART_DELAY_MS)
      }, FOLLOW_UP_TIMEOUT_MS)
    }

    followUp.onaudiostart = resetSilenceTimeout
    followUp.onaudioend = resetSilenceTimeout
    followUp.onend = () => console.debug('[WakeWord] followUp ended')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    followUp.onerror = (event: any) => {
      console.debug('[WakeWord] followUp error:', event.error)
      followUpActiveRef.current = false
      handleRecognitionError(event.error)
      setState('continuous-listening')
      setTimeout(() => { if (!disabledRef.current) startContinuousRef.current() }, RESTART_DELAY_MS)
    }

    followUp.start()
    followUpRef.current = followUp
    resetSilenceTimeout()
  }, [setText, submit])

  const startContinuous = useCallback(() => {
    console.debug('[WakeWord] startContinuous called', { SR: !!SR, wake_word: soul?.wake_word, disabled: disabledRef.current })
    if (!SR || !soul?.wake_word || disabledRef.current || startingRef.current) return
    startingRef.current = true
    setState('starting')
    const recognition = new SR()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = navigator.language

    const wakeWord = soul.wake_word
    if (wakeWord) {
      try { recognition.phrases = [wakeWord, ...(soul.aliases || [])] } catch {}
    }

    recognition.onstart = () => console.debug('[WakeWord] recognition started, listening for:', wakeWord)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      if (disabledRef.current) return
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          const transcript = event.results[i][0].transcript
          console.debug('[WakeWord] transcript:', transcript, '| checking against wake word:', soul?.wake_word)
          const matched = matchWakeWord(transcript, soul)
          console.debug('[WakeWord] matchWakeWord result:', matched)
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
      console.debug('[WakeWord] recognition error:', code)
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
      console.debug('[WakeWord] recognition ended, disabled:', disabledRef.current, 'followUpActive:', followUpActiveRef.current)
      startingRef.current = false
      if (disabledRef.current || followUpActiveRef.current) return
      setTimeout(() => {
        if (!disabledRef.current && !followUpActiveRef.current) startContinuousRef.current()
      }, RESTART_DELAY_MS)
    }

    recognition.start()
    continuousRef.current = recognition
    setState('continuous-listening')
  }, [soul, textareaRef, triggerWakeEvent, startFollowUp])

  // Keep ref in sync so onend closures always call the latest version
  startContinuousRef.current = startContinuous

  useEffect(() => {
    disabledRef.current = !enabled
    if (enabled && soul?.wake_word && SR) {
      startContinuousRef.current()
    } else {
      startingRef.current = false
      continuousRef.current?.abort()
      followUpRef.current?.abort()
      setState('disabled')
    }
    return () => {
      disabledRef.current = true
      startingRef.current = false
      followUpActiveRef.current = false
      continuousRef.current?.abort()
      followUpRef.current?.abort()
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, soul?.wake_word])

  return null
}
