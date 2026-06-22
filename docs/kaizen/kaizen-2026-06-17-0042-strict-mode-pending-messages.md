# Kaizen: user message not visible on first send in new chat (Strict Mode double-invoke)

**Date:** 2026-06-17 00:42
**Type:** Bug Fix
**Files:** `ui/components/chat/ChatView.tsx`
**Severity:** High

## Symptom

When sending the first message in a new chat during development, the user's message bubble was invisible while the AI was thinking/streaming. The ThinkingBlock appeared at the top of the chat, and the user message only "appeared" once the response finished — pushing the thinking block down to its correct position below the message.

## Investigation

The user described the behavior as the thinking block being rendered at the top of the chat with no user message above it, then the message appearing later and everything shifting down. This ruled out a pure scroll-position issue (which would leave the message rendered but off-screen).

Two `useEffect` hooks in `ChatView.tsx` were the primary suspects:

1. **The session-reset effect** (line 60): clears all streaming state including `pendingMessages` whenever `sessionId` changes — including on initial mount.
2. **The initial-message effect** (line 156): populates `pendingMessages` and sends the message via WebSocket, guarded by `initialSentRef.current` to prevent duplicate sends in React's Strict Mode.

The initial lead was that the session-reset effect was clearing `pendingMessages` after the initial-message effect populated them. But on a normal production mount, React fires effects in definition order: the session-reset effect fires first (clearing `[]→[]` — a no-op), then the initial-message effect fires (populating). This works fine.

The actual trigger was React Strict Mode (enabled by default in Next.js 15 dev mode). Strict Mode double-invokes effects:
- First mount: session-reset clears (no-op), initial-message populates `pendingMessages` and sets `initialSentRef.current = true`.
- Second mount: session-reset clears `pendingMessages` back to `[]`; initial-message is **skipped** because `initialSentRef.current` is already `true`.

`pendingMessages` stayed empty. The WebSocket connection (preserved by `useWebSocket`'s deferred-close logic) still connected and streamed events, so `thinking_delta` events populated `streamingBlocks` → the ThinkingBlock rendered alone. The user message only appeared after `turn_completed` invalidated the messages query, refetching the persisted conversation from the API.

## Root Cause

The session-reset effect used a bare `[sessionId]` dependency — it ran on any `sessionId` change, including the identical-value "change" that Strict Mode's second mount triggers. There was no mechanism to distinguish "real session change" from "Strict Mode remount with the same sessionId."

The `initialSentRef` guard in the initial-message effect was correct for its purpose (prevent duplicate sends) but created an asymmetry: the session-reset effect was unguarded and could invalidate state that the initial-message effect couldn't repopulate.

## Fix

Added a `prevSessionIdRef` (`useRef<string | null>(null)`) to track the actual previous `sessionId`. The session-reset effect now only clears state when `prevSessionIdRef.current !== sessionId` — i.e., when the sessionId *actually* changed. After the check, `prevSessionIdRef.current` is updated.

This works because `useRef` persists across Strict Mode's double mount. On the first mount, the ref is `null` and `sessionId` is a string → mismatch → clears (correct, no state yet). On the Strict Mode second mount, the ref is already the old `sessionId` from the first mount → match → skips the clear. On a real session change (user switches sessions), the values differ → clears correctly.

## Lesson

**Strict Mode double-invoke isn't just about refs and cleanup functions — it affects the relative timing of `useEffect` hooks without cleanup.** Two effects where one is guarded and the other isn't can produce state corruption on the second mount.

The pattern to detect "real changes vs. remounts" with a `useRef` comparison is a general solution for this class of bug. Any `useEffect` that clears state on a prop change should consider whether Strict Mode's second mount with the same prop value could corrupt state set by another effect on the first mount.

Also worth noting: the `useWebSocket` hook's deferred-close logic (explicitly designed for Strict Mode) meant the WebSocket *survived* the double-invoke, creating the full illusion of a working connection while the rendering path was broken. If the WS had disconnected on the second mount, the failure mode would have been more obvious (no response at all).
