import type { WakeWordHandle, WakeWordOptions } from './wakeWorklet'
import { ClipRecorder } from './ClipRecorder'

type State = 'idle' | 'listening' | 'captured' | 'transcribing' | 'done'

interface Deps {
  getStream: () => Promise<MediaStream>
  transcribe: (b: Blob, model?: string) => Promise<string>
  onTranscript?: (text: string) => void
  // Optional: when provided, start() arms a wake-word engine instead of just
  // holding a stream. Injected as a factory so the controller stays unit-testable.
  createWake?: (opts?: WakeWordOptions) => Promise<WakeWordHandle>
  wakeOpts?: WakeWordOptions
  model?: string
}

// Single owner of the microphone. The wake engine and the clip recorder never
// run concurrently — on detect, the engine is stopped (releasing its stream)
// before the recorder opens one (REL-001 / ADR-002, sequential-handoff variant).
export class VoiceController {
  state: State = 'idle'
  private stream: MediaStream | null = null
  private wake: WakeWordHandle | null = null
  private recorder: ClipRecorder | null = null

  constructor(private deps: Deps) {}

  async start(): Promise<void> {
    if (this.state !== 'idle') return  // idempotent — never two owners

    if (this.deps.createWake) {
      this.state = 'listening'
      this.wake = await this.deps.createWake(this.deps.wakeOpts)
      this.wake.on('detect', () => { void this._onWake() })
      await this.wake.load()
      await this.wake.start()  // engine owns its own mic stream while listening
      return
    }

    // No wake engine (e.g. tests / push-to-talk only): just hold one stream.
    this.stream = await this.deps.getStream()
    this.state = 'listening'
  }

  stop(): void {
    void this.wake?.stop()
    this.wake = null
    this.recorder?.stop()
    this.recorder = null
    this.stream?.getTracks().forEach(t => t.stop())
    this.stream = null
    this.state = 'idle'
  }

  // Wake fired → release the engine's mic, record one command clip, transcribe.
  private async _onWake(): Promise<void> {
    if (this.state !== 'listening') return  // ignore during cooldown / busy
    this.state = 'captured'
    await this.wake?.stop()  // hand off the mic — never two streams at once

    const text = await this._recordAndTranscribe()
    if (text) this.deps.onTranscript?.(text)

    // Re-arm the wake engine for the next activation. stop() clears this.wake,
    // so a still-present engine means we were not torn down mid-transcription.
    if (this.wake) {
      this.state = 'listening'
      await this.wake.start()
    }
  }

  // Push-to-talk path: skip the wake word, record one clip directly.
  async captureOnce(model?: string): Promise<string> {
    if (this.state !== 'idle') return ''
    this.state = 'captured'
    try {
      const text = await this._recordAndTranscribe(model)
      this.stop()
      return text
    } catch {
      this.stop()
      return ''
    }
  }

  // Open one stream, record until end-of-speech, transcribe. Returns '' when no
  // speech was detected (cost gate) — caller makes zero transcription request.
  private async _recordAndTranscribe(model?: string): Promise<string> {
    const stream = await this.deps.getStream()
    this.stream = stream
    const ctx = new AudioContext({ sampleRate: 16000 })

    const blob = await new Promise<Blob | null>((resolve) => {
      this.recorder = new ClipRecorder(stream, ctx)
      this.recorder.start({ onSilence: (clip) => resolve(clip) })
    })

    stream.getTracks().forEach(t => t.stop())
    this.stream = null
    void ctx.close()
    this.recorder = null

    if (!blob) return ''  // cost gate: no speech → no ASR call
    this.state = 'transcribing'
    return await this.deps.transcribe(blob, model ?? this.deps.model)
  }
}
