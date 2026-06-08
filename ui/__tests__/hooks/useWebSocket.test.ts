import { vi, test, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useWebSocket } from '../../hooks/useWebSocket'

test('useWebSocket connects to /ws/turn', () => {
  const sockets: any[] = []
  class MockWS {
    url: string; onopen = null; onmessage = null; onclose = null
    constructor(url: string) { this.url = url; sockets.push(this) }
    close = vi.fn()
    send = vi.fn()
  }
  globalThis.WebSocket = MockWS as any

  renderHook(() => useWebSocket('s_test', vi.fn()))
  expect(sockets).toHaveLength(1)
  expect(sockets[0].url).toContain('/ws/sessions/s_test')
})

test('useWebSocket skips connection when sessionId is null', () => {
  const sockets: any[] = []
  class MockWS { constructor(url: string) { sockets.push(url) } }
  globalThis.WebSocket = MockWS as any

  renderHook(() => useWebSocket(null, vi.fn()))
  expect(sockets).toHaveLength(0)
})
