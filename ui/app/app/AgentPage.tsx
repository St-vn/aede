'use client'
import React, { useState, useCallback } from 'react'
import { Layout } from '@/components/Layout'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { EmptyState } from '@/components/empty/EmptyState'
import { ChatView } from '@/components/chat/ChatView'
import { useSessions, useSessionMessages, useCreateSession, useDeleteSession } from '@/hooks/useSession'
import { InputBar } from '@/components/input/InputBar'
import { useQueryClient } from '@tanstack/react-query'

export function AgentPage() {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [initialMessage, setInitialMessage] = useState<string>('')
  const [activeProjectDir, setActiveProjectDir] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)
  const qc = useQueryClient()

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
    setActiveProjectDir(null)
  }, [])

  const handleSelectSession = (id: string) => {
    setActiveId(id)
    setActiveProjectDir(null)
    qc.invalidateQueries({ queryKey: ['workspaceInfo'] })
    qc.invalidateQueries({ queryKey: ['workspaceFiles'] })
  }

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession.mutateAsync(id)
      if (activeId === id) {
        setActiveId(null)
        setInitialMessage('')
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
      alert('Failed to delete session')
    }
  }

  const handleResumeBranch = async (parentId: string) => {
    try {
      const session = await createSession.mutateAsync({ model: 'claude-sonnet-4', parentId })
      setActiveId(session.id)
      setActiveProjectDir(null)
    } catch (err) {
      console.error('Failed to create branch:', err)
    }
  }

  const handleOpenProject = (dir: string | null) => {
    setActiveId(null)
    setInitialMessage('')
    setActiveProjectDir(dir)
  }

  const handleSendNewSession = async (content: string, model?: string) => {
    try {
      const selectedModel = model || 'claude-sonnet-4'
      const session = await createSession.mutateAsync({
        model: selectedModel,
        projectDir: activeProjectDir ?? undefined,
      })
      setInitialMessage(content)
      setActiveId(session.id)
      setActiveProjectDir(null)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  if (!mounted) {
    return <div className="h-dvh bg-background" />
  }

  return (
    <Layout
      sidebar={
        <Sidebar sessions={sessions} activeSessionId={activeId} activeProjectDir={activeProjectDir}
          onSelectSession={handleSelectSession} onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession} onResumeBranch={handleResumeBranch}
          onOpenProject={handleOpenProject} />
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
            <EmptyState onOpenProject={handleOpenProject} projectName={activeProjectDir ? activeProjectDir.split(/[\\/]/).pop() || activeProjectDir : undefined} activeProjectDir={activeProjectDir} />
          </div>
          <div className="max-w-[760px] mx-auto w-full">
            <InputBar onSend={handleSendNewSession} disabled={createSession.isPending} sessionId={activeId} projectDir={activeProjectDir} />
          </div>
        </div>
      )}
    />
  )
}
