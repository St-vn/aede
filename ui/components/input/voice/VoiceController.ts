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
      // Surface engine errors — the engine swallows mel/embedding/VAD failures
      // into an 'error' event; without this listener detection dies silently.
      this.wake.on('error', (e) => { console.error('[voice] wake engine error:', e) })
      this.wake.on('detect', (p) => { console.debug('[voice] wake detected:', p); void this._onWake().catch(err => console.error('[voice] onWake failed:', err)) })
      await this.wake.load()
      await this.wake.start()  // engine owns its own mic stream while listening
      console.debug('[voice] wake engine armed, listening for wake word')
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

    try {
      const text = await this._recordAndTranscribe()
      if (text) this.deps.onTranscript?.(text)
    } catch (err) {
      console.error('[voice] capture/transcribe failed:', err)
    } finally {
      // Always re-arm for the next activation unless stop() tore us down
      // (stop() clears this.wake).
      if (this.wake) {
        this.state = 'listening'
        await this.wake.start().catch(e => console.error('[voice] re-arm failed:', e))
      }
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
    console.debug('[voice] recording command clip…')
    const stream = await this.deps.getStream()
    this.stream = stream
    const ctx = new AudioContext()  // default rate; recording, not 16k wake inference

    const blob = await new Promise<Blob | null>((resolve) => {
      this.recorder = new ClipRecorder(stream, ctx)
      this.recorder.start({
        onSpeech: () => console.debug('[voice] speech detected, recording…'),
        onSilence: (clip) => {
          console.debug('[voice] clip done. hadSpeech=', this.recorder?.hadSpeech, 'bytes=', clip?.size ?? 0)
          resolve(clip)
        },
      })
    })

    stream.getTracks().forEach(t => t.stop())
    this.stream = null
    void ctx.close()
    this.recorder = null

    if (!blob) { console.debug('[voice] no speech after wake — cost gate, no ASR call'); return '' }
    this.state = 'transcribing'
    const m = model ?? this.deps.model
    console.debug('[voice] transcribing (deps.transcribe closure carries the ASR model)…')
    const text = await this.deps.transcribe(blob, m)
    console.debug('[voice] transcript:', JSON.stringify(text))
    return text
  }
}
