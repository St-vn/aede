import { describe, it, expect, vi } from 'vitest'
import { transcribe } from '@/components/input/voice/AsrClient'

vi.mock('@/components/input/voice/WebSpeechProvider', () => ({
  transcribeViaWebSpeech: vi.fn(async () => 'web speech floor'),
}))

describe('AsrClient', () => {
  it('returns backend text when provider keyed', async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ text: 'cloud text', provider: 'groq' }) })) as any
    globalThis.fetch = fetchMock
    const out = await transcribe(new Blob([new Uint8Array([1])]), 'whisper-large-v3-turbo')
    expect(out).toBe('cloud text')
    // Must hit the Python backend, absolute URL, no trailing slash.
    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toMatch(/^https?:\/\/[^/]+\/api\/voice\/transcribe$/)
  })
  it('falls back to web speech on {fallback:webspeech}', async () => {
    globalThis.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ fallback: 'webspeech' }) })) as any
    const out = await transcribe(new Blob([new Uint8Array([1])]), 'whisper-large-v3-turbo')
    expect(out).toBe('web speech floor')
  })
})
