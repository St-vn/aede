import { describe, it, expect, vi } from 'vitest'
import { VoiceController } from '@/components/input/voice/VoiceController'

describe('VoiceController', () => {
  it('never opens a second stream while one is active', async () => {
    let openStreams = 0
    const mockStream = { getTracks: () => [] } as any
    const getStream = vi.fn(async () => { openStreams++; expect(openStreams).toBeLessThanOrEqual(1); return mockStream })
    const vc = new VoiceController({ getStream, transcribe: async () => 'x' })
    await vc.start()
    await vc.start() // second call must be a no-op while active
    expect(getStream).toHaveBeenCalledTimes(1)
    vc.stop()
  })

  it('transitions idle→listening on start and back to idle on stop', async () => {
    const mockStream = { getTracks: () => [] } as any
    const vc = new VoiceController({ getStream: async () => mockStream, transcribe: async () => 'x' })
    expect(vc.state).toBe('idle')
    await vc.start()
    expect(vc.state).toBe('listening')
    vc.stop()
    expect(vc.state).toBe('idle')
  })
})
