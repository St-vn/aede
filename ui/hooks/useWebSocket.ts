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
  // Pending deferred-close timer; lets StrictMode's remount cancel a close.
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Defer the socket close one macrotask so a StrictMode remount can cancel it.
  const scheduleClose = (socket: WebSocket): ReturnType<typeof setTimeout> =>
    setTimeout(() => {
      console.log('[WS] cleanup (deferred) - readyState:', socket.readyState)
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
    }, 0)

  useEffect(() => {
    if (!sessionId) return

    // React 18/19 StrictMode double-invokes effects in dev: mount → cleanup →
    // mount. Closing the socket synchronously in cleanup tears down a connection
    // a brand-new turn is about to run on — the backend then sees
    // WebSocketDisconnect and CANCELS the in-flight (possibly gated) turn,
    // silently dropping the user's edit.
    //
    // Fix: defer the close one macrotask. If StrictMode immediately remounts,
    // this effect re-runs first, cancels the pending close, and reuses the live
    // socket — so the connection survives the dev double-invoke. A real unmount
    // or session change lets the timer fire and closes cleanly.
    if (closeTimerRef.current !== null) {
      clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }

    const url = `${WS_BASE}/ws/sessions/${sessionId}`
    const existing = ws.current
    if (
      existing &&
      existing.url === url &&
      (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)
    ) {
      // Reuse the surviving socket; just re-bind the message handler.
      existing.onmessage = (e) => onEventRef.current(JSON.parse(e.data) as WSEvent)
      return () => {
        closeTimerRef.current = scheduleClose(existing)
      }
    }

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
      closeTimerRef.current = scheduleClose(socket)
    }
  }, [sessionId])

  const send = useCallback((msg: any) => {
    const payload = msg.type === 'user_turn' ? {
      type: 'user_message',
      content: msg.content,
      ...(msg.model ? { model: msg.model } : {}),
      ...(msg.gate_mode ? { gate_mode: msg.gate_mode } : {}),
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
