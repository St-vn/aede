'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { UserMessage } from './UserMessage'
import { AssistantMessage } from './AssistantMessage'
import { ToolCallCard } from './ToolCallCard'
import { GateCard } from './GateCard'
import { InputBar } from '@/components/input/InputBar'
import { useWebSocket, type WSEvent } from '@/hooks/useWebSocket'
import { ContextBar } from './ContextBar'
import { LearningsChip } from './LearningsChip'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

interface Message { id: string; role: 'user' | 'assistant'; content: string; created_at: string; is_branch_point?: boolean }
interface ToolCall { id: string; name: string; args: Record<string, unknown>; status: string; output?: string; durationMs?: number }
interface GateRequest { gateId: string; toolName: string; args: Record<string, unknown> }

interface Props { sessionId: string; messages: Message[]; initialMessage?: string; onClearInitialMessage?: () => void; onOpenSettings?: (tab?: string) => void; onOpenHelp?: () => void }

const _stripRich = (text: string): string =>
  text.replace(/\[\/?\w+(?:[ \t]\w+)*\]/g, '').replace(/\r/g, '')

export function ChatView({ sessionId, messages, initialMessage, onClearInitialMessage, onOpenSettings, onOpenHelp }: Props) {
  const [streamingText, setStreamingText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
  const [gate, setGate] = useState<GateRequest | null>(null)
  const [pendingMessages, setPendingMessages] = useState<{ content: string; id: string }[]>([])
  const containerRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const prevMessagesLenRef = useRef(messages.length)

  useEffect(() => {
    if (messages.length > prevMessagesLenRef.current && streamingText && !isStreaming) {
      setStreamingText('')
    }
    prevMessagesLenRef.current = messages.length
  }, [messages.length, streamingText, isStreaming])

  useEffect(() => {
    if (!isStreaming && messages.length > 0) {
      setPendingMessages([])
    }
  }, [isStreaming, messages.length])

  const onEvent = useCallback((ev: WSEvent) => {
    if (ev.type === 'text_delta') {
      setIsStreaming(true)
      setStreamingText(t => t + (ev.text as string))
    } else if (ev.type === 'console_message') {
      setIsStreaming(true)
      const content = _stripRich(ev.content as string || '')
      if (!content.trim()) return
      setStreamingText(t => t + content + '\n')
    } else if (ev.type === 'tool_call') {
      setToolCalls(tc => [...tc, { id: ev.id as string, name: ev.name as string,
        args: ev.args as Record<string, unknown>, status: 'running' }])
    } else if (ev.type === 'tool_result') {
      setToolCalls(tc => tc.map(c => c.id === ev.id
        ? { ...c, status: ev.status as string, output: ev.output as string, durationMs: ev.duration_ms as number }
        : c))
    } else if (ev.type === 'gate_request') {
      setGate({ gateId: ev.gate_id as string, toolName: ev.tool_name as string, args: ev.args as Record<string, unknown> })
    } else if (ev.type === 'turn_done' || ev.type === 'turn_completed') {
      setIsStreaming(false)
      setGate(null)
      queryClient.invalidateQueries({ queryKey: ['messages', sessionId] })
    } else if (ev.type === 'error') {
      toast.error(ev.message as string, { duration: 8000 })
    }
  }, [sessionId, queryClient])

  const { send } = useWebSocket(sessionId, onEvent)
  const initialSentRef = useRef(false)
  const prevSessionRef = useRef(sessionId)
  if (prevSessionRef.current !== sessionId) {
    prevSessionRef.current = sessionId
    initialSentRef.current = false
  }

  useEffect(() => {
    if (initialMessage && !initialSentRef.current) {
      initialSentRef.current = true
      const id = `pending-${Date.now()}`
      setPendingMessages(p => [...p, { content: initialMessage, id }])
      send({ type: 'user_turn', content: initialMessage })
      setIsStreaming(true)
      onClearInitialMessage?.()
    }
  }, [initialMessage, send, onClearInitialMessage])

  // Auto-scroll to bottom using scroll container viewport directly
  useEffect(() => {
    const viewport = containerRef.current?.querySelector('[data-slot="scroll-area-viewport"]')
    if (viewport) {
      viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages, streamingText])

  const handleSend = (content: string, model?: string) => {
    const id = `pending-${Date.now()}`
    setPendingMessages(p => [...p, { content, id }])
    send({ type: 'user_turn', content, model })
    setStreamingText('')
    setIsStreaming(true)
  }

  const handleGateDecision = ({ gateId, decision, message }: { gateId: string; decision: string; message?: string }) => {
    const payload: Record<string, unknown> = { type: 'gate_response', gate_id: gateId, decision }
    if (message) payload.redirect_msg = message
    send(payload)
    setGate(null)
  }

  const inputDisabled = isStreaming || !!gate

  return (
    <div ref={containerRef} className="flex-1 flex flex-col min-h-0">
      <ScrollArea className="flex-1 min-h-0 px-4">
        <div className="max-w-[760px] mx-auto py-4 space-y-1">
          {messages.map(m =>
            m.is_branch_point
              ? <div key={m.id} className="flex items-center gap-3 py-4 px-4 select-none">
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-xs text-muted-foreground shrink-0">Branch point</span>
                  <div className="flex-1 h-px bg-border" />
                </div>
              : m.role === 'user'
                ? <UserMessage key={m.id} content={m.content} timestamp={m.created_at} />
                : <AssistantMessage key={m.id} content={m.content} isStreaming={false} />
          )}
          {pendingMessages.map(pm => (
            <UserMessage key={pm.id} content={pm.content} timestamp={new Date().toISOString()} />
          ))}
          {toolCalls.map(tc => (
            <ToolCallCard key={tc.id} toolName={tc.name} status={tc.status as 'running' | 'success' | 'error' | 'denied'}
              args={tc.args} output={tc.output} durationMs={tc.durationMs} />
          ))}
          {streamingText && (
            <AssistantMessage content={streamingText} isStreaming={isStreaming} />
          )}
          {gate && (
            <GateCard gateId={gate.gateId} toolName={gate.toolName}
              args={gate.args} onDecision={handleGateDecision} />
          )}
        </div>
      </ScrollArea>
      <ContextBar sessionId={sessionId} />
      <div className="max-w-[760px] mx-auto w-full px-4 pb-1 flex items-center justify-end">
        <LearningsChip sessionId={sessionId} />
      </div>
      <div className="max-w-[760px] mx-auto w-full">
        <InputBar onSend={handleSend} disabled={inputDisabled} sessionId={sessionId} />
      </div>
    </div>
  )
}
