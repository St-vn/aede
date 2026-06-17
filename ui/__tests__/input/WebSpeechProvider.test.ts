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

  it('resolves "" on end with no result (silence is not an error)', async () => {
    const handlers: Record<string, any> = {}
    class FakeSR {
      continuous = false; interimResults = false; lang = ''
      set onresult(fn: any) { handlers.onresult = fn }
      set onerror(fn: any) { handlers.onerror = fn }
      set onend(fn: any) { handlers.onend = fn }
      start() { setTimeout(() => handlers.onend(), 0) }  // ends with no result
      stop() {}
      abort() {}
    }
    ;(window as any).SpeechRecognition = FakeSR
    await expect(transcribeViaWebSpeech()).resolves.toBe('')
  })

  it('rejects only on permission errors', async () => {
    const handlers: Record<string, any> = {}
    class FakeSR {
      continuous = false; interimResults = false; lang = ''
      set onresult(fn: any) { handlers.onresult = fn }
      set onerror(fn: any) { handlers.onerror = fn }
      set onend(fn: any) { handlers.onend = fn }
      start() { setTimeout(() => handlers.onerror({ error: 'not-allowed' }), 0) }
      stop() {}
      abort() {}
    }
    ;(window as any).SpeechRecognition = FakeSR
    await expect(transcribeViaWebSpeech()).rejects.toThrow('not-allowed')
  })

  it('resolves "" on no-speech error (not a real failure)', async () => {
    const handlers: Record<string, any> = {}
    class FakeSR {
      continuous = false; interimResults = false; lang = ''
      set onresult(fn: any) { handlers.onresult = fn }
      set onerror(fn: any) { handlers.onerror = fn }
      set onend(fn: any) { handlers.onend = fn }
      start() { setTimeout(() => handlers.onerror({ error: 'no-speech' }), 0) }
      stop() {}
      abort() {}
    }
    ;(window as any).SpeechRecognition = FakeSR
    await expect(transcribeViaWebSpeech()).resolves.toBe('')
  })
})
