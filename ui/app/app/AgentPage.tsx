'use client'
import React, { useState, useCallback } from 'react'
import { Layout } from '@/components/Layout'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { EmptyState } from '@/components/empty/EmptyState'
import { ChatView } from '@/components/chat/ChatView'
import { useSessions, useSessionMessages, useCreateSession, useDeleteSession } from '@/hooks/useSession'
import { InputBar } from '@/components/input/InputBar'

export function AgentPage() {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [initialMessage, setInitialMessage] = useState<string>('')
  const [mounted, setMounted] = useState(false)
  
  const { data: sessions = [] } = useSessions()
  const { data: messages = [] } = useSessionMessages(activeId)
  const createSession = useCreateSession()
  const deleteSession = useDeleteSession()

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const handleNewSession = useCallback(() => {
    setActiveId(null)
    setInitialMessage('')
  }, [])

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession.mutateAsync(id)
      if (activeId === id) {
        handleNewSession()
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
      alert('Failed to delete session')
    }
  }

  const handleSendNewSession = async (content: string, model?: string) => {
    try {
      const selectedModel = model || 'claude-sonnet-4'
      const session = await createSession.mutateAsync(selectedModel)
      setInitialMessage(content)
      setActiveId(session.id)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  if (!mounted) {
    return <div className="h-dvh bg-background" /> // Static background for SSR
  }

  return (
    <Layout
      sidebar={
        <Sidebar sessions={sessions} activeSessionId={activeId}
          onSelectSession={setActiveId} onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession} />
      }
      centerPane={activeId ? (
        <ChatView
          sessionId={activeId}
          messages={messages}
          initialMessage={initialMessage}
          onClearInitialMessage={() => setInitialMessage('')}
        />
      ) : (
        <div className="flex-1 flex flex-col min-h-0 justify-between">
          <div className="flex-1 overflow-y-auto min-h-0">
            <EmptyState />
          </div>
          <div className="max-w-[760px] mx-auto w-full">
            <InputBar onSend={handleSendNewSession} disabled={createSession.isPending} />
          </div>
        </div>
      )}
    />
  )
}
