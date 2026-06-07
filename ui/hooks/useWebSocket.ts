'use client'
import { useEffect, useRef, useCallback } from 'react'
import { WS_BASE } from '@/lib/api'

export type WSEvent = { type: string } & Record<string, unknown>

export function useWebSocket(
  sessionId: string | null,
  onEvent: (ev: WSEvent) => void
) {
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return
    const socket = new WebSocket(`${WS_BASE}/ws/turn`)
    ws.current = socket
    socket.onmessage = (e) => onEvent(JSON.parse(e.data) as WSEvent)
    return () => { socket.close(); ws.current = null }
  }, [sessionId, onEvent])

  const send = useCallback((msg: any) => {
    const payload = msg.type === 'user_turn' ? {
      type: 'user_message',
      session_id: sessionId,
      content: msg.content,
    } : msg

    const attemptSend = () => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify(payload))
        return true
      }
      return false
    }

    if (!attemptSend()) {
      const interval = setInterval(() => {
        if (attemptSend()) {
          clearInterval(interval)
        }
      }, 100)
      setTimeout(() => clearInterval(interval), 5000)
    }
  }, [sessionId])

  return { send }
}
