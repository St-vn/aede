'use client'
import React, { useState, useCallback } from 'react'
import { Layout } from '@/components/Layout'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { EmptyState } from '@/components/empty/EmptyState'
import { ChatView } from '@/components/chat/ChatView'
import { useSessionMessages, useCreateSession, useDeleteSession, useUpdateSessionMode } from '@/hooks/useSession'
import { InputBar } from '@/components/input/InputBar'
import { useQueryClient } from '@tanstack/react-query'
import { useConfig } from '@/hooks/useConfig'
import { SettingsModal, type SettingsTabId } from '@/components/settings/SettingsModal'

export function AgentPage() {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [initialMessage, setInitialMessage] = useState<string>('')
  const [activeProjectDir, setActiveProjectDir] = useState<string | null>(null)
  const [currentModel, setCurrentModel] = useState('claude-sonnet-4')
  const [currentMode, setCurrentMode] = useState('normal')
  const [mounted, setMounted] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsTab, setSettingsTab] = useState<SettingsTabId | undefined>(undefined)
  const qc = useQueryClient()

  const { data: messages = [] } = useSessionMessages(activeId)
  const { data: config } = useConfig()
  const createSession = useCreateSession()
  const deleteSession = useDeleteSession()
  const updateSessionMode = useUpdateSessionMode()

  // Sync model from persisted config on load
  React.useEffect(() => {
    if (config?.model && config.model !== currentModel) {
      setCurrentModel(config.model)
    }
  }, [config?.model])

  // Sync mode from persisted config on load
  React.useEffect(() => {
    if (config?.gate_mode && config.gate_mode !== currentMode) {
      setCurrentMode(config.gate_mode)
    }
  }, [config?.gate_mode])

  const handleModeChange = useCallback((mode: string) => {
    setCurrentMode(mode)
    if (activeId) {
      updateSessionMode.mutate({ sessionId: activeId, gateMode: mode })
    }
  }, [activeId, updateSessionMode])

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
      // Persist the selected permission mode to the new session BEFORE the WS
      // turn fires. The server reads session.gate_mode per turn, so without
      // this a mode chosen on a fresh chat (no activeId yet) would be lost and
      // the turn would run under the default mode, re-prompting for shell/edits.
      if (currentMode && currentMode !== 'normal') {
        await updateSessionMode.mutateAsync({ sessionId: session.id, gateMode: currentMode })
      }
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
    <>
      <Layout
        sidebar={
          <Sidebar activeSessionId={activeId} activeProjectDir={activeProjectDir}
            onSelectSession={handleSelectSession} onNewSession={handleNewSession}
            onDeleteSession={handleDeleteSession} onResumeBranch={handleResumeBranch}
            onOpenProject={handleOpenProject} onOpenSettings={() => setSettingsOpen(true)} />
        }
        centerPane={activeId ? (
            <ChatView
              sessionId={activeId}
              messages={messages}
              initialMessage={initialMessage}
              onClearInitialMessage={() => setInitialMessage('')}
              onOpenSettings={(tab) => { setSettingsTab(tab as SettingsTabId); setSettingsOpen(true) }}
              defaultModel={currentModel} onModelChange={setCurrentModel}
              mode={currentMode} onModeChange={handleModeChange}
              onRewind={(newSessionId) => {
                setActiveId(newSessionId)
                setActiveProjectDir(null)
              }}
            />
        ) : (
          <div className="flex-1 flex flex-col min-h-0 justify-between">
            <div className="flex-1 overflow-y-auto min-h-0">
              <EmptyState onOpenProject={handleOpenProject} projectName={activeProjectDir ? activeProjectDir.split(/[\\/]/).pop() || activeProjectDir : undefined} activeProjectDir={activeProjectDir} />
            </div>
            <div className="max-w-[760px] mx-auto w-full">
              <InputBar onSend={handleSendNewSession} disabled={createSession.isPending} sessionId={activeId} projectDir={activeProjectDir}
                onOpenSettings={(tab) => { setSettingsTab(tab as SettingsTabId); setSettingsOpen(true) }}
                model={currentModel} onModelChange={setCurrentModel}
                mode={currentMode} onModeChange={handleModeChange} />
            </div>
          </div>
        )}
      />
      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} initialTab={settingsTab} sessionId={activeId} projectDir={activeProjectDir} />
    </>
  )
}
