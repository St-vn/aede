'use client'
import { useEffect, useRef, useCallback } from 'react'
import { WS_BASE } from '@/lib/api'

export type WSEvent = { type: string } & Record<string, unknown>

export function useWebSocket(
  sessionId: string | null,
  onEvent: (ev: WSEvent) => void
) {
  const ws = useRef<WebSocket | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    if (!sessionId) return

    const url = `${WS_BASE}/ws/sessions/${sessionId}`
    console.log('[WS] creating socket:', url)
    const socket = new WebSocket(url)
    ws.current = socket

    socket.onopen = () => {
      console.log('[WS] onopen - readyState:', socket.readyState, 'session:', sessionId)
    }

    socket.onmessage = (e) => {
      onEventRef.current(JSON.parse(e.data) as WSEvent)
    }

    socket.onerror = (err) => {
      console.error('[WS] onerror:', err, 'session:', sessionId)
    }

    socket.onclose = (ev) => {
      console.log('[WS] onclose - code:', ev.code, 'reason:', ev.reason, 'wasClean:', ev.wasClean, 'session:', sessionId)
    }

    return () => {
      console.log('[WS] cleanup - readyState:', socket.readyState, 'session:', sessionId)
      socket.onopen = null
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
      if (socket.readyState !== WebSocket.CONNECTING) {
        socket.close()
      }
      if (ws.current === socket) {
        ws.current = null
      }
    }
  }, [sessionId])

  const send = useCallback((msg: any) => {
    const payload = msg.type === 'user_turn' ? {
      type: 'user_message',
      content: msg.content,
      ...(msg.model ? { model: msg.model } : {}),
    } : msg

    const attemptSend = () => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        console.log('[WS] send success - sending payload type:', payload.type)
        ws.current.send(JSON.stringify(payload))
        return true
      }
      return false
    }

    if (!attemptSend()) {
      console.log('[WS] send deferred - socket not OPEN yet, retrying...')
      let attempts = 0
      let sent = false
      const interval = setInterval(() => {
        attempts++
        if (!sent && attemptSend()) {
          sent = true
          console.log('[WS] send succeeded after', attempts, 'retries')
          clearInterval(interval)
        }
      }, 100)
      setTimeout(() => {
        clearInterval(interval)
        if (!sent) {
          console.log('[WS] send TIMEOUT - socket never reached OPEN. readyState was:', ws.current?.readyState)
        }
      }, 5000)
    }
  }, [])

  return { send }
}
