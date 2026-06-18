import React from 'react'
import { vi, test, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DaemonTab from '@/components/settings/tabs/DaemonTab'

beforeEach(() => {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/daemon/status')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ running: true, pid: 123, port: 9876 }),
      })
    }
    if (url.includes('/daemon/timers')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ timers: [] }) })
    }
    if (url.includes('/daemon/cron')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ jobs: [] }) })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('renders daemon status section', () => {
  render(<DaemonTab />)
  expect(screen.getByText(/daemon/i)).toBeInTheDocument()
})

test('invalid cron expression shows error', async () => {
  render(<DaemonTab />)

  const addCronBtn = await screen.findByRole('button', { name: /add cron/i })
  fireEvent.click(addCronBtn)

  fireEvent.change(screen.getByPlaceholderText(/daily_report/i), {
    target: { value: 'test_action' },
  })

  fireEvent.change(screen.getByPlaceholderText(/0 9 \* \* \*/i), {
    target: { value: 'invalid' },
  })

  const addBtn = screen.getByRole('button', { name: /^add$/i })
  fireEvent.click(addBtn)

  expect(await screen.findByText(/invalid cron/i)).toBeInTheDocument()
})
