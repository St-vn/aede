import { describe, test, expect } from 'vitest'
import { API_BASE, WS_BASE } from '@/lib/api'

describe('API_BASE', () => {
  test('defaults to localhost:8000', () => {
    expect(API_BASE).toContain('localhost:8000')
  })
  test('never contains raw API key placeholder', () => {
    expect(API_BASE.toUpperCase()).not.toContain('ANTHROPIC')
  })
})

describe('WS_BASE', () => {
  test('starts with ws://', () => {
    expect(WS_BASE).toMatch(/^ws:\/\//)
  })
  test('derives from API_BASE (same host/port)', () => {
    const apiHost = API_BASE.replace(/^https?:\/\//, '')
    const wsHost = WS_BASE.replace(/^wss?:\/\//, '')
    expect(wsHost).toBe(apiHost)
  })
})
