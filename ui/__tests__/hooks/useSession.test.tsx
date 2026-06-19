import React from 'react'
import { vi, test, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSessions, useRewind } from '../../hooks/useSession'

const wrapper = ({ children }: any) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: 0 } } })}>
    {children}
  </QueryClientProvider>
)

beforeEach(() => {
  vi.restoreAllMocks()
})

test('useSessions returns list on success', async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve([
      { id: 's1', title: 'test', model: 'sonnet', parent_id: null, created_at: new Date().toISOString() },
    ]),
  }) as any

  const { result } = renderHook(() => useSessions(), { wrapper })
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(Array.isArray(result.current.data)).toBe(true)
  expect(result.current.data).toHaveLength(1)
})

test('useRewind calls rewind endpoint with correct params', async () => {
  const mockFetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ id: 'new-session-id' }),
  })
  globalThis.fetch = mockFetch

  const { result } = renderHook(() => useRewind(), { wrapper })
  const newSession = await result.current.rewind('s1', 'm1', false)

  expect(mockFetch).toHaveBeenCalledWith(
    expect.stringContaining('/api/sessions/s1/rewind'),
    expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      body: expect.stringContaining('"message_id":"m1"'),
    })
  )
  expect(newSession).toEqual({ id: 'new-session-id' })
})
