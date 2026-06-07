import React from 'react'
import { vi, test, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSessions } from '../../hooks/useSession'

const wrapper = ({ children }: any) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: 0 } } })}>
    {children}
  </QueryClientProvider>
)

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
