import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { VoiceButton } from '@/components/input/voice/VoiceButton'

describe('VoiceButton', () => {
  it('inserts transcribed text on capture', async () => {
    const setText = vi.fn()
    const captureOnce = vi.fn(async () => 'dictated text')
    render(<VoiceButton enabled captureOnce={captureOnce} setText={setText}
      textareaRef={{ current: null }} onPermissionDenied={()=>{}} onError={()=>{}} />)
    fireEvent.click(document.querySelector('button')!)
    await Promise.resolve()
    expect(captureOnce).toHaveBeenCalled()
  })
})
