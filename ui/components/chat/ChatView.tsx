'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { UserMessage } from './UserMessage'
import { AssistantMessage } from './AssistantMessage'
import { ToolCallCard } from './ToolCallCard'
import { ThinkingBlock } from './ThinkingBlock'
import { GateCard } from './GateCard'
import { GateBatchCard } from './GateBatchCard'
import { QuestionCard } from './QuestionCard'
import { InputBar } from '@/components/input/InputBar'
import type { ImageAttachment } from '@/components/input/ImagePreviewBar'
import { useWebSocket, type WSEvent } from '@/hooks/useWebSocket'
import { ContextBar } from './ContextBar'
import { LearningsChip } from './LearningsChip'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ChevronDown } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { useRewind } from '@/hooks/useSession'

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

interface Props { sessionId: string; messages: Message[]; initialMessage?: string; onClearInitialMessage?: () => void; onOpenSettings?: (tab?: string) => void; onOpenHelp?: () => void; defaultModel?: string; onModelChange?: (model: string) => void; mode?: string; onModeChange?: (mode: string) => void; onRewind?: (newSessionId: string) => void }

const _stripRich = (text: string): string =>
  text.replace(/\[\/?\w+(?:[ \t]\w+)*\]/g, '').replace(/\r/g, '')

function parseImagesFromMarkdown(content: string): { text: string; images: ImageAttachment[] } {
  const imgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g
  const images: ImageAttachment[] = []
  let imgId = 0
  const text = content.replace(imgRegex, (match, alt: string, url: string) => {
    if (url.startsWith('data:image/')) {
      const id = `rewind-${++imgId}`
      const mimeMatch = url.match(/data:(image\/[^;]+);/)
      const mime = mimeMatch ? mimeMatch[1] : 'image/png'
      const ext = mime.split('/')[1] || 'png'
      images.push({ id, dataUrl: url, mime, filename: alt || `rewound-image.${ext}` })
      return ''
    }
    return match
  })
  return { text: text.trim(), images }
}

// React key for a tool block. OpenAI-style providers (e.g. DeepSeek) may emit
// tool calls with an empty/missing id; falling back to a per-index key keeps
// sibling keys unique ("two children with the same key 0").
export const toolBlockKey = (b: { id?: string }, idx: number): string =>
  b.id || `tool-${idx}`

export function ChatView({ sessionId, messages, initialMessage, onClearInitialMessage, onOpenSettings, onOpenHelp, defaultModel, onModelChange, mode, onModeChange, onRewind }: Props) {
  const [streamingText, setStreamingText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  // streamingBlocks holds interleaved thinking+tool blocks in seq order during streaming.
  const [streamingBlocks, setStreamingBlocks] = useState<StreamingBlock[]>([])
  const [gates, setGates] = useState<GateRequest[]>([])
  interface AskUserQuestion {
    header: string
    question: string
    type: 'single' | 'multi' | 'text'
    options?: string[]
    allow_custom?: boolean
    allow_notes?: boolean
    required?: boolean
  }
  const [askUserRequests, setAskUserRequests] = useState<{ questionId: string; questions: AskUserQuestion[] }[]>([])
  const [pendingMessages, setPendingMessages] = useState<{ content: string; id: string }[]>([])
  const queueRef = useRef<string[]>([])
  const [queuedMessages, setQueuedMessages] = useState<string[]>([])
  const containerRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const { rewind } = useRewind()
  const prevMessagesLenRef = useRef(messages.length)
  const prevSessionIdRef = useRef<string | null>(null)
  const turnStartRef = useRef<number | null>(null)
  const [lastTurnDurationMs, setLastTurnDurationMs] = useState<number | null>(null)
  const sendRef = useRef<((msg: Record<string, unknown>) => void) | null>(null)
  const onEventRef = useRef<((ev: WSEvent) => void) | null>(null)
  const [rewindKey, setRewindKey] = useState(0)
  const [rewindText, setRewindText] = useState<string | undefined>(undefined)
  const [rewindImages, setRewindImages] = useState<ImageAttachment[] | undefined>(undefined)
  const [nearBottom, setNearBottom] = useState(true)

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
      const incoming = {
        questionId: ev.question_id as string,
        questions: (ev.questions as AskUserQuestion[]) || [],
      }
      setAskUserRequests(reqs => {
        const idx = reqs.findIndex(r => r.questionId === incoming.questionId)
        if (idx !== -1) {
          // Replace in place — prevents duplicate-key stacking on re-ask
          return reqs.map((r, i) => i === idx ? incoming : r)
        }
        return [...reqs, incoming]
      })
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
      // Dequeue next message if any are queued
      if (queueRef.current.length > 0) {
        const [next, ...rest] = queueRef.current
        queueRef.current = rest
        setQueuedMessages(rest)
        const id = `pending-${Date.now()}`
        setPendingMessages(p => [...p, { content: next, id }])
        sendRef.current?.({ type: 'user_turn', content: next })
        setStreamingText('')
        setStreamingBlocks([])
        turnStartRef.current = Date.now()
        setLastTurnDurationMs(null)
      } else {
        setIsStreaming(false)
        setStreamingBlocks([])
        setGates([])
        setAskUserRequests([])
        setStreamingText('')
      }
      queryClient.invalidateQueries({ queryKey: ['messages', sessionId] })
    } else if (ev.type === 'error') {
      const msg = ev.message as string
      // A stale "Chat about this" can target a question whose future already
      // resolved (answered, or turn ended); the backend replies with an
      // "Unknown question_id" error. That race is benign — don't toast it.
      if (msg.startsWith('Unknown question_id')) return
      toast.error(msg, { duration: 8000 })
    }
  }, [sessionId, queryClient])
  onEventRef.current = onEvent

  const { send } = useWebSocket(sessionId, (ev) => onEventRef.current?.(ev))
  sendRef.current = send
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
      send({ type: 'user_turn', content: initialMessage, gate_mode: mode })
      setIsStreaming(true)
      onClearInitialMessage?.()
    }
  }, [initialMessage, send, onClearInitialMessage])

  // Track whether user is near bottom via scroll events (for the scroll-to-bottom button)
  useEffect(() => {
    const viewport = containerRef.current?.querySelector('[data-slot="scroll-area-viewport"]')
    if (!viewport) return
    const handleScroll = () => {
      const threshold = 75
      setNearBottom(viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < threshold)
    }
    handleScroll()
    viewport.addEventListener('scroll', handleScroll, { passive: true })
    return () => viewport.removeEventListener('scroll', handleScroll)
  }, [])

  // Initial scroll to bottom when session loads with messages
  useEffect(() => {
    if (messages.length === 0) return
    const viewport = containerRef.current?.querySelector('[data-slot="scroll-area-viewport"]')
    if (!viewport) return
    viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'instant' })
  }, [sessionId, messages.length])

  // Auto-scroll when new content arrives if user is near bottom (inline DOM check)
  useEffect(() => {
    const viewport = containerRef.current?.querySelector('[data-slot="scroll-area-viewport"]')
    if (!viewport) return
    const threshold = 100
    const isNearBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < threshold
    if (isNearBottom) {
      viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' })
    }
  }, [messages, streamingText, streamingBlocks, gates, askUserRequests])

  const scrollToBottom = () => {
    const viewport = containerRef.current?.querySelector('[data-slot="scroll-area-viewport"]')
    if (!viewport) return
    setNearBottom(true)
    viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' })
  }

  const handleStop = useCallback(() => {
    send({ type: 'stop' })
  }, [send])

  const handleQueue = useCallback((content: string) => {
    queueRef.current = [...queueRef.current, content]
    setQueuedMessages([...queueRef.current])
  }, [])

  const handleSend = (content: string, model?: string) => {
    const id = `pending-${Date.now()}`
    setPendingMessages(p => [...p, { content, id }])
    send({ type: 'user_turn', content, model, gate_mode: mode })
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

  const handleAskUserAnswer = (questionId: string, answers: Record<string, string | string[] | { value: string | string[]; notes: string }>) => {
    send({ type: 'ask_user_response', question_id: questionId, answers })
    setAskUserRequests(reqs => reqs.filter(r => r.questionId !== questionId))
  }

  const handleQuestionChat = (questionId: string, questionText: string, comment: string) => {
    // Optimistically echo the comment so the user sees their message land
    // immediately; the question card stays pending until the agent replies.
    setPendingMessages(p => [...p, { content: comment, id: `chat-${Date.now()}` }])
    send({ type: 'ask_user_chat', question_id: questionId, question: questionText, comment })
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
      }).catch(() => { })
    }
  }, [onModelChange])

  const handleRewind = useCallback(async (messageId: string, opts: { mode: 'truncate' | 'fork'; revertCode: boolean }) => {
    const msg = messages.find(m => m.id === messageId)
    const parsed = msg ? parseImagesFromMarkdown(msg.content) : null
    try {
      const result = await rewind(sessionId, messageId, opts) as { id: string }
      if (opts.mode === 'truncate') {
        if (parsed) {
          setRewindText(parsed.text)
          setRewindImages(parsed.images.length > 0 ? parsed.images : undefined)
          setRewindKey(k => k + 1)
        }
        queryClient.invalidateQueries({ queryKey: ['sessions'] })
        queryClient.invalidateQueries({ queryKey: ['messages', sessionId] })
      } else {
        queryClient.invalidateQueries({ queryKey: ['sessions'] })
        onRewind?.(result.id)
      }
    } catch (err) {
      console.error('Rewind failed:', err)
      toast.error('Rewind failed — see console for details')
    }
  }, [sessionId, messages, rewind, queryClient, onRewind])

  const inputDisabled = gates.length > 0 || askUserRequests.length > 0

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
      <div className="relative flex flex-col flex-1 min-h-0">
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
                  ? <UserMessage key={m.id} content={m.content} timestamp={m.created_at} messageId={m.id} onRewind={handleRewind} />
                  : <React.Fragment key={m.id}>
                    <AssistantMessage
                      content={m.content}
                      isStreaming={false}
                      thinking={m.thinking}
                      thinkingSegments={m.thinking_segments}
                      turnDurationMs={getTurnDuration(m, mi)}
                    />
                    {!isStreaming && m.tool_calls?.map((tc, ti) => (
                      <ToolCallCard key={toolBlockKey(tc, ti)} toolName={tc.name} status={tc.status as 'running' | 'success' | 'error' | 'denied'}
                        args={tc.args} output={tc.output} durationMs={tc.durationMs} />
                    ))}
                  </React.Fragment>
            )}
            {pendingMessages.map(pm => (
              <UserMessage key={pm.id} content={pm.content} timestamp={new Date().toISOString()} />
            ))}
            {/* Interleaved streaming blocks: thinking + tool calls in execution order */}
            {sortedBlocks.map((block, bi) =>
              block.kind === 'thinking'
                ? <ThinkingBlock key={`thinking-${block.seq}`} thinking={block.text} isStreaming={isStreaming} />
                : <ToolCallCard key={toolBlockKey(block, bi)} toolName={block.name} status={block.status as 'running' | 'success' | 'error' | 'denied'}
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
              <QuestionCard key={req.questionId} request={req} onAnswer={handleAskUserAnswer} onChat={handleQuestionChat} />
            ))}
          </div>
        </ScrollArea>
        {!nearBottom && (
          <div className="absolute bottom-2 left-0 right-0 flex justify-center pointer-events-none z-10">
            <button onClick={scrollToBottom}
              className="pointer-events-auto w-7 h-7 flex items-center justify-center rounded-full bg-card/90 hover:bg-card transition-colors"
              aria-label="Scroll to bottom">
              <ChevronDown className="w-3.5 h-3.5 text-white" />
            </button>
          </div>
        )}
      </div>
      <ContextBar sessionId={sessionId} />
      <div className="max-w-[760px] mx-auto w-full px-4 pb-1 flex items-center justify-end">
        <LearningsChip sessionId={sessionId} />
      </div>
      {queuedMessages.length > 0 && (
        <div className="max-w-[760px] mx-auto w-full px-4 pb-1">
          <div className="flex flex-wrap gap-1.5">
            {queuedMessages.map((msg, i) => (
              <span key={i} className="inline-flex items-center gap-1 text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-md truncate max-w-[200px]">
                <span className="shrink-0">#{i + 1}</span>
                <span className="truncate">{msg}</span>
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="max-w-[760px] mx-auto w-full">
        <InputBar key={rewindKey} onSend={handleSend} disabled={inputDisabled} isStreaming={isStreaming}
          onStop={handleStop} onQueue={handleQueue} sessionId={sessionId}
          defaultModel={defaultModel} onModelChange={handleModelChange}
          mode={mode} onModeChange={onModeChange}
          prefillText={rewindText} prefillImages={rewindImages} />
      </div>
    </div>
  )
}
