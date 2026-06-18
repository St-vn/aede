'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { UserMessage } from './UserMessage'
import { AssistantMessage } from './AssistantMessage'
import { ToolCallCard } from './ToolCallCard'
import { ThinkingBlock } from './ThinkingBlock'
import { GateCard } from './GateCard'
import { GateBatchCard } from './GateBatchCard'
import { AskUserCard } from './AskUserCard'
import { InputBar } from '@/components/input/InputBar'
import { useWebSocket, type WSEvent } from '@/hooks/useWebSocket'
import { ContextBar } from './ContextBar'
import { LearningsChip } from './LearningsChip'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiFetch } from '@/lib/api'

interface ThinkingSegment { text: string; seq: number }
interface Message { id: string; role: 'user' | 'assistant'; content: string; created_at: string; is_branch_point?: boolean; thinking?: string; thinking_segments?: ThinkingSegment[]; turn_duration_ms?: number | null; tool_calls?: ToolCall[] }
interface ToolCall { id: string; name: string; args: Record<string, unknown>; status: string; output?: string; durationMs?: number; streamingOutput?: string }
interface GateRequestOption { id: string; label: string; key: string }
interface GateRequest { gateId: string; toolName: string; args: Record<string, unknown>; mode?: string; reason?: string; options?: GateRequestOption[] }

// A streaming block is either an in-progress thinking segment or a tool call,
// ordered by seq so they render in true execution order.
type StreamingBlock =
  | { kind: 'thinking'; seq: number; text: string }
  | { kind: 'tool'; seq: number; id: string; name: string; args: Record<string, unknown>; status: string; output?: string; durationMs?: number; streamingOutput?: string }

interface Props { sessionId: string; messages: Message[]; initialMessage?: string; onClearInitialMessage?: () => void; onOpenSettings?: (tab?: string) => void; onOpenHelp?: () => void; defaultModel?: string; onModelChange?: (model: string) => void; mode?: string; onModeChange?: (mode: string) => void }

const _stripRich = (text: string): string =>
  text.replace(/\[\/?\w+(?:[ \t]\w+)*\]/g, '').replace(/\r/g, '')

export function ChatView({ sessionId, messages, initialMessage, onClearInitialMessage, onOpenSettings, onOpenHelp, defaultModel, onModelChange, mode, onModeChange }: Props) {
  const [streamingText, setStreamingText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  // streamingBlocks holds interleaved thinking+tool blocks in seq order during streaming.
  const [streamingBlocks, setStreamingBlocks] = useState<StreamingBlock[]>([])
  const [gates, setGates] = useState<GateRequest[]>([])
  const [askUserRequests, setAskUserRequests] = useState<{ questionId: string; question: string; type?: string; choices?: string[] }[]>([])
  const [pendingMessages, setPendingMessages] = useState<{ content: string; id: string }[]>([])
  const containerRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const prevMessagesLenRef = useRef(messages.length)
  const prevSessionIdRef = useRef<string | null>(null)
  const turnStartRef = useRef<number | null>(null)
  const [lastTurnDurationMs, setLastTurnDurationMs] = useState<number | null>(null)

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

  useEffect(() => {
    if (prevSessionIdRef.current !== sessionId) {
      setStreamingBlocks([])
      setGates([])
      setAskUserRequests([])
      setStreamingText('')
      setIsStreaming(false)
      setPendingMessages([])
      turnStartRef.current = null
      setLastTurnDurationMs(null)
    }
    prevSessionIdRef.current = sessionId
  }, [sessionId])

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
      setIsStreaming(true)
      const id = ev.id as string
      const name = ev.name as string
      const args = ev.args as Record<string, unknown>
      const seq = typeof ev.seq === 'number' ? ev.seq as number : 999
      setStreamingBlocks(blocks => {
        const existing = blocks.find(b => b.kind === 'tool' && b.id === id)
        if (existing) {
          // Later updates carry populated args (ACP rawInput); merge without
          // resetting a status already advanced to success/error.
          return blocks.map(b =>
            b.kind === 'tool' && b.id === id
              ? { ...b, name, args: Object.keys(args).length ? args : b.args }
              : b
          )
        }
        return [...blocks, { kind: 'tool' as const, seq, id, name, args, status: 'running' }]
      })
    } else if (ev.type === 'thinking_start') {
      setIsStreaming(true)
    } else if (ev.type === 'thinking_delta') {
      setIsStreaming(true)
      const seq = typeof ev.seq === 'number' ? ev.seq as number : 0
      const text = ev.text as string
      setStreamingBlocks(blocks => {
        // Find an existing thinking block with this seq to append to.
        const idx = blocks.findIndex(b => b.kind === 'thinking' && b.seq === seq)
        if (idx !== -1) {
          return blocks.map((b, i) =>
            i === idx && b.kind === 'thinking'
              ? { ...b, text: b.text + text }
              : b
          )
        }
        return [...blocks, { kind: 'thinking' as const, seq, text }]
      })
    } else if (ev.type === 'tool_output_delta') {
      setStreamingBlocks(blocks => blocks.map(b =>
        b.kind === 'tool' && b.id === (ev.call_id as string)
          ? { ...b, streamingOutput: (b.streamingOutput || '') + (ev.text as string) }
          : b
      ))
    } else if (ev.type === 'tool_result') {
      setStreamingBlocks(blocks => blocks.map(b =>
        b.kind === 'tool' && b.id === (ev.id as string)
          ? { ...b, status: ev.status as string, output: ev.output as string, durationMs: ev.duration_ms as number }
          : b
      ))
    } else if (ev.type === 'gate_request') {
      setGates(gs => [...gs, {
        gateId: ev.gate_id as string,
        toolName: ev.tool_name as string,
        args: ev.args as Record<string, unknown>,
        mode: ev.mode as string | undefined,
        reason: ev.reason as string | undefined,
        options: ev.options as GateRequestOption[] | undefined,
      }])
    } else if (ev.type === 'ask_user_request') {
      setAskUserRequests(reqs => [...reqs, {
        questionId: ev.question_id as string,
        question: ev.question as string,
        type: ev.question_type as string | undefined,
        choices: ev.choices as string[] | undefined,
      }])
    } else if (ev.type === 'ask_user_response') {
      setAskUserRequests(reqs => reqs.filter(r => r.questionId !== ev.question_id))
    } else if (ev.type === 'turn_done' || ev.type === 'turn_completed') {
      // Use server-provided turn_duration_ms if available, fall back to client-side timing
      if (typeof ev.turn_duration_ms === 'number') {
        setLastTurnDurationMs(ev.turn_duration_ms)
      } else if (turnStartRef.current) {
        setLastTurnDurationMs(Date.now() - turnStartRef.current)
      }
      turnStartRef.current = null
      setIsStreaming(false)
      setStreamingBlocks([])
      setGates([])
      setAskUserRequests([])
      setStreamingText('')
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
    setStreamingBlocks([])
    turnStartRef.current = Date.now()
    setLastTurnDurationMs(null)
  }

  const handleGateDecision = ({ gateId, decision, message }: { gateId: string; decision: string; message?: string }) => {
    const payload: Record<string, unknown> = { type: 'gate_response', gate_id: gateId, decision }
    if (message) payload.redirect_msg = message
    send(payload)
    setGates(gs => gs.filter(g => g.gateId !== gateId))
  }

  const handleAskUserAnswer = (questionId: string, answer: string) => {
    send({ type: 'ask_user_response', question_id: questionId, answer })
    setAskUserRequests(reqs => reqs.filter(r => r.questionId !== questionId))
  }

  const handleModelChange = useCallback((model: string) => {
    onModelChange?.(model)
    const acpPrefixes = ['claude-code', 'codex', 'gemini', 'cline', 'cursor', 'goose', 'agy']
    const isAcp = acpPrefixes.some(p => model === p || model.startsWith(p + '/'))
    if (isAcp) {
      const baseAgent = model.split('/')[0]
      apiFetch('/api/acp/warmup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: baseAgent }),
      }).catch(() => {})
    }
  }, [onModelChange])

  const inputDisabled = isStreaming || gates.length > 0 || askUserRequests.length > 0

  // Sort streaming blocks by seq for display.
  const sortedBlocks = [...streamingBlocks].sort((a, b) => a.seq - b.seq)

  // Resolve the turn duration for a given message: prefer persisted DB value,
  // then the ephemeral client-side value for the most recent turn.
  const getTurnDuration = (msg: Message, idx: number): number | undefined => {
    // The persisted value from DB is the source of truth when available.
    if (typeof msg.turn_duration_ms === 'number' && msg.turn_duration_ms > 0) {
      return msg.turn_duration_ms
    }
    // For the last assistant message, fall back to the ephemeral value
    // that arrived via the turn_completed WS event.
    if (idx === lastAssistantIdx && lastTurnDurationMs !== null) {
      return lastTurnDurationMs
    }
    return undefined
  }

  // Find the index of the last assistant message so we can show turn duration on it.
  const lastAssistantIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant' && !messages[i].is_branch_point) return i
    }
    return -1
  })()

  return (
    <div ref={containerRef} className="flex-1 flex flex-col min-h-0">
      <ScrollArea className="flex-1 min-h-0 px-4">
        <div className="max-w-[760px] mx-auto py-4 px-4 space-y-1">
          {messages.map((m, mi) =>
            m.is_branch_point
              ? <div key={m.id} className="flex items-center gap-3 py-4 px-4 select-none">
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-xs text-muted-foreground shrink-0">Branch point</span>
                  <div className="flex-1 h-px bg-border" />
                </div>
              : m.role === 'user'
                ? <UserMessage key={m.id} content={m.content} timestamp={m.created_at} />
                : <React.Fragment key={m.id}>
                    <AssistantMessage
                      content={m.content}
                      isStreaming={false}
                      thinking={m.thinking}
                      thinkingSegments={m.thinking_segments}
                      turnDurationMs={getTurnDuration(m, mi)}
                    />
                    {!isStreaming && m.tool_calls?.map(tc => (
                      <ToolCallCard key={tc.id} toolName={tc.name} status={tc.status as 'running' | 'success' | 'error' | 'denied'}
                        args={tc.args} output={tc.output} durationMs={tc.durationMs} />
                    ))}
                  </React.Fragment>
          )}
          {pendingMessages.map(pm => (
            <UserMessage key={pm.id} content={pm.content} timestamp={new Date().toISOString()} />
          ))}
          {/* Interleaved streaming blocks: thinking + tool calls in execution order */}
          {sortedBlocks.map(block =>
            block.kind === 'thinking'
              ? <ThinkingBlock key={`thinking-${block.seq}`} thinking={block.text} isStreaming={isStreaming} />
              : <ToolCallCard key={block.id} toolName={block.name} status={block.status as 'running' | 'success' | 'error' | 'denied'}
                  args={block.args} output={block.output} durationMs={block.durationMs} streamingOutput={block.streamingOutput} />
          )}
          {(streamingText || isStreaming) && (
            <AssistantMessage content={streamingText} isStreaming={isStreaming} turnDurationMs={lastTurnDurationMs ?? undefined} />
          )}
          {gates.length > 1 && (
            <GateBatchCard gates={gates} onDecision={(gateId, decision) =>
              handleGateDecision({ gateId, decision })} />
          )}
          {gates.length === 1 && (
            <GateCard gateId={gates[0].gateId} toolName={gates[0].toolName}
              args={gates[0].args} mode={gates[0].mode} reason={gates[0].reason}
              options={gates[0].options} onDecision={handleGateDecision} />
          )}
          {askUserRequests.map(req => (
            <AskUserCard key={req.questionId} request={req} onAnswer={handleAskUserAnswer} />
          ))}
        </div>
      </ScrollArea>
      <ContextBar sessionId={sessionId} />
      <div className="max-w-[760px] mx-auto w-full px-4 pb-1 flex items-center justify-end">
        <LearningsChip sessionId={sessionId} />
      </div>
      <div className="max-w-[760px] mx-auto w-full">
        <InputBar onSend={handleSend} disabled={inputDisabled} sessionId={sessionId}
          defaultModel={defaultModel} onModelChange={handleModelChange}
          mode={mode} onModeChange={onModeChange} />
      </div>
    </div>
  )
}
