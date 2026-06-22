import { describe, it, expect } from 'vitest'
import { isSilent, shouldStopOnSilence } from '@/components/input/voice/ClipRecorder'

describe('energy gate', () => {
  it('flags frames near the 128 midpoint as silent', () => {
    expect(isSilent(new Uint8Array([128, 128, 128]), 5)).toBe(true)   // flat = silence
    expect(isSilent(new Uint8Array([10, 250, 10]), 5)).toBe(false)    // loud
  })

  it('treats deviation exactly at threshold as not-silent (>= threshold is sound)', () => {
    // mean abs deviation from 128 is exactly 5 → not silent
    expect(isSilent(new Uint8Array([133, 123]), 5)).toBe(false)
    // mean abs deviation 4 → silent
    expect(isSilent(new Uint8Array([132, 124]), 5)).toBe(true)
  })

  it('stops only after N consecutive silent frames FOLLOWING speech', () => {
    expect(shouldStopOnSilence({ hadSpeech: true, silentFrames: 30, threshold: 30 })).toBe(true)
    expect(shouldStopOnSilence({ hadSpeech: true, silentFrames: 10, threshold: 30 })).toBe(false)
  })

  it('never stops if speech was never detected (cost gate owns that path)', () => {
    expect(shouldStopOnSilence({ hadSpeech: false, silentFrames: 999, threshold: 30 })).toBe(false)
  })
})
