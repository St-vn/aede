import React from 'react'
import { test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SettingsModal } from '@/components/settings/SettingsModal'

const qc = new QueryClient({ defaultOptions: { queries: { retry: 0 } } })

function Wrapper({ children }: any) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

test("tabs list is scrollable to prevent clipping on short viewports", () => {
  render(<SettingsModal open onOpenChange={() => {}} sessionId="sess-1" projectDir="/tmp" />, { wrapper: Wrapper })
  const tabsList = screen.getByRole("tablist")
  expect(tabsList.className).toMatch(/overflow-y-auto|overflow-auto|max-h/)
})

test("settings modal includes Daemon tab", () => {
  render(<SettingsModal open onOpenChange={() => {}} sessionId="sess-1" projectDir="/tmp" />, { wrapper: Wrapper })
  expect(screen.getByRole("tab", { name: /daemon/i })).toBeInTheDocument()
})
