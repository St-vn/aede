'use client'
import React, { createContext, useContext } from 'react'

interface UserContextValue { userId: string; isLocal: boolean }

const Ctx = createContext<UserContextValue>({ userId: 'local', isLocal: true })

export function UserContextProvider({ children }: { children: React.ReactNode }) {
  return <Ctx.Provider value={{ userId: 'local', isLocal: true }}>{children}</Ctx.Provider>
}

export const useUser = () => useContext(Ctx)
