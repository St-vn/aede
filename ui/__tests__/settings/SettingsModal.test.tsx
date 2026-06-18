import React from 'react'
import { test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SettingsModal } from '@/components/settings/SettingsModal'

const qc = new QueryClient({ defaultOptions: { queries: { retry: 0 } } })

function Wrapper({ children }: any) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

test("settings modal includes Daemon tab", () => {
  render(<SettingsModal open onOpenChange={() => {}} sessionId="sess-1" projectDir="/tmp" />, { wrapper: Wrapper })
  expect(screen.getByRole("tab", { name: /daemon/i })).toBeInTheDocument()
})
