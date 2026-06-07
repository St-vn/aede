import React from 'react'
import { test, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useUser, UserContextProvider } from '../../contexts/UserContext'

test('provides local user stub in Phase 2', () => {
  const { result } = renderHook(() => useUser(), {
    wrapper: ({ children }) => <UserContextProvider>{children}</UserContextProvider>,
  })
  expect(result.current.userId).toBe('local')
  expect(result.current.isLocal).toBe(true)
})
