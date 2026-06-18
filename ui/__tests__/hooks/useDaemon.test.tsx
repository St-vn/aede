import { vi, test, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { SWRConfig } from 'swr'
import { useDaemonStatus } from '@/hooks/useDaemon'

test('useDaemonStatus fetches /api/daemon/status', async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ running: true, pid: 123, port: 9876 }),
  })
  const { result } = renderHook(() => useDaemonStatus(), {
    wrapper: ({ children }) => (
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
        {children}
      </SWRConfig>
    ),
  })
  await waitFor(() => expect(result.current.data?.running).toBe(true))
})
