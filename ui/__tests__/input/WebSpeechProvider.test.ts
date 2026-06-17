import { describe, it, expect, vi } from 'vitest'
import { transcribeViaWebSpeech } from '@/components/input/voice/WebSpeechProvider'

describe('WebSpeechProvider', () => {
  it('resolves with the final transcript', async () => {
    const handlers: Record<string, any> = {}
    class FakeSR {
      continuous = false; interimResults = false; lang = ''
      set onresult(fn: any) { handlers.onresult = fn }
      set onerror(fn: any) { handlers.onerror = fn }
      set onend(fn: any) { handlers.onend = fn }
      start() { setTimeout(() => handlers.onresult({ results: [[{ transcript: 'floor text' }]] }), 0) }
      stop() {}
      abort() {}
    }
    ;(window as any).SpeechRecognition = FakeSR
    const text = await transcribeViaWebSpeech()
    expect(text).toBe('floor text')
  })
})
