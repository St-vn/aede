import { describe, it, expect, vi } from 'vitest'
import { VoiceController } from '@/components/input/voice/VoiceController'
import { ClipRecorder } from '@/components/input/voice/ClipRecorder'

describe('VoiceController', () => {
  it('never opens a second stream while one is active', async () => {
    let openStreams = 0
    const mockStream = { getTracks: () => [] } as any
    const getStream = vi.fn(async () => { openStreams++; expect(openStreams).toBeLessThanOrEqual(1); return mockStream })
    const vc = new VoiceController({ getStream, transcribe: async () => 'x' })
    await vc.start()
    await vc.start()
    expect(getStream).toHaveBeenCalledTimes(1)
    vc.stop()
  })

  it('frees AudioContext and stops tracks when ClipRecorder.start() throws', async () => {
    const track = { stop: vi.fn() }
    const mockStream = { getTracks: () => [track] } as any
    const getStream = vi.fn(async () => mockStream)

    const closeFn = vi.fn()
    const OrigAudioContext = globalThis.AudioContext
    globalThis.AudioContext = class { close = closeFn } as any

    vi.spyOn(ClipRecorder.prototype, 'start').mockImplementation(
      function () { throw new Error('simulated start failure') },
    )

    const vc = new VoiceController({ getStream, transcribe: async () => 'x' })
    const result = await vc.captureOnce()

    globalThis.AudioContext = OrigAudioContext
    vi.restoreAllMocks()

    expect(result).toBe('')
    expect(closeFn).toHaveBeenCalled()
    expect(track.stop).toHaveBeenCalled()
  })

  it('"transitions idle listening on start and back to idle on stop"', async () => {
    const mockStream = { getTracks: () => [] } as any
    const vc = new VoiceController({ getStream: async () => mockStream, transcribe: async () => 'x' })
    expect(vc.state).toBe('idle')
    await vc.start()
    expect(vc.state).toBe('listening')
    vc.stop()
    expect(vc.state).toBe('idle')
  })
})